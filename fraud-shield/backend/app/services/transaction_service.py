"""Transaction Processing and Orchestration Service.

Coordinates end-to-end transaction evaluation:
  1. Behavioral Feature Extraction (<10ms)
  2. Unsupervised Isolation Forest Anomaly Scoring (<15ms)
  3. Deterministic Security Rules & Sigmoid Score Blending (<5ms)
  4. Decision Mapping (ALLOW, CHALLENGE_OTP, FREEZE_REVIEW)
  5. Persistent Storage & Tamper-Evident Audit Logging (Phase 7)
  6. Sliding-Window State Management
"""
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session
import numpy as np

from app.database.session import get_db_context
from app.models.risk_assessment import RiskAssessment
from app.models.transaction import Transaction
from app.repositories.audit_repo import audit_repo
from app.repositories.otp_repo import otp_repo
from app.repositories.transaction_repo import transaction_repo
from app.repositories.user_repo import user_repo
from app.schemas.transaction import (
    RuleTriggerInfo,
    TransactionDetail,
    TransactionEvaluateRequest,
    TransactionEvaluateResponse,
)
from app.security.hashing import hash_identifier, mask_user_id, mask_vpa
from app.services.anomaly_detector import anomaly_detector_service
from app.services.feature_engineering import feature_service
from app.services.risk_engine import risk_engine_service

logger = logging.getLogger(__name__)


class PersistenceError(RuntimeError):
    """Raised when persistent database or audit logging fails during transaction evaluation."""


class TransactionService:
    """Coordinates risk scoring, lifecycle transitions, database persistence, and audit logging."""

    MAX_CACHE_SIZE: int = 500

    def __init__(self):
        # Bounded in-memory cache for high-speed lookup and client-facing field enrichment
        self._transactions: Dict[str, Dict] = {}
        self._chronological_txn_ids: List[str] = []

    def evaluate_transaction(
        self,
        request: TransactionEvaluateRequest,
        db: Optional[Session] = None,
    ) -> TransactionEvaluateResponse:
        """Execute real-time end-to-end evaluation within sub-50ms latency budget.

        Extracts sliding-window features, runs Isolation Forest scoring, evaluates
        deterministic rules, maps operational status, persists records to SQLite,
        and appends to the sequential cryptographic audit hash-chain.
        """
        t_start = time.perf_counter()
        txn_id = str(uuid.uuid4())
        txn_timestamp = request.timestamp or datetime.now(timezone.utc)
        user_hash = hash_identifier(request.user_id)
        masked_vpa_str = mask_vpa(request.recipient_vpa)
        raw_device_id = getattr(request, "device_id", None)
        device_hash = hash_identifier(raw_device_id) if raw_device_id else None

        # 1. Behavioral Feature Extraction (<10ms SLA)
        features = feature_service.extract_features(
            user_id=request.user_id,
            amount=request.amount,
            timestamp=txn_timestamp,
            recipient_vpa=request.recipient_vpa,
            device_hash=device_hash,
        )
        feature_vector = np.array(
            [features[col] for col in feature_service.FEATURE_COLUMNS],
            dtype=np.float32,
        )

        # 2. ML Anomaly Detection (<15ms SLA)
        ml_score = anomaly_detector_service.predict_anomaly_score(feature_vector)

        # 2b. Historical 24h Failed OTP Attempts Lookup (O(1) cached)
        from app.services.otp_service import otp_service
        failed_otp_attempts = otp_service.get_recent_failed_attempts(user_hash)

        # 3. Composite Risk Engine Decision (<5ms SLA)
        decision = risk_engine_service.evaluate(
            ml_score=ml_score,
            features=features,
            recipient_vpa=request.recipient_vpa,
            failed_otp_attempts=failed_otp_attempts,
        )

        # 4. Map Operational Status & Lifecycle Action
        session_id = None
        if decision.action == "ALLOW":
            status = "APPROVED"
        elif decision.action == "CHALLENGE_OTP":
            status = "PENDING_VERIFICATION"
            # Cryptographic challenge session identifier
            session_id = f"otp_sess_{uuid.uuid4().hex[:16]}"
        else:  # FREEZE_REVIEW
            status = "SECURITY_FLAGGED"

        total_latency_ms = (time.perf_counter() - t_start) * 1000.0

        # Construct rule info schemas
        rule_infos = [
            RuleTriggerInfo(
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                severity=r["severity"],
                penalty=r["penalty"],
                reason=r["reason"],
            )
            for r in decision.triggered_rules
        ]

        response = TransactionEvaluateResponse(
            txn_id=txn_id,
            user_id=request.user_id,
            user_hash=user_hash,
            amount=request.amount,
            recipient_vpa=request.recipient_vpa,
            recipient_vpa_masked=masked_vpa_str,
            timestamp=txn_timestamp,
            channel=request.channel,
            device_hash=device_hash,
            status=status,
            risk_tier=decision.risk_tier,
            composite_score=decision.composite_score,
            ml_score=decision.ml_score,
            challenge_required=decision.challenge_required,
            session_id=session_id,
            triggered_rules=rule_infos,
            explanation=decision.explanation,
            latency_ms=round(total_latency_ms, 3),
        )

        # 5. Database Persistence & Tamper-Evident Audit Logging (atomic; raises on failure)
        self._persist_evaluation(
            request=request,
            response=response,
            decision=decision,
            features=features,
            rule_infos=rule_infos,
            db=db,
        )

        # 6. Only update sliding-window & cache after persistent commit succeeds
        feature_service.commit_transaction(
            user_id=request.user_id,
            amount=request.amount,
            timestamp=txn_timestamp,
            recipient_vpa=request.recipient_vpa,
            device_hash=device_hash,
            is_flagged=(decision.risk_tier == "HIGH"),
        )

        record = response.model_dump()
        record["created_at"] = txn_timestamp.isoformat()
        record["risk_assessment"] = {
            "composite_score": decision.composite_score,
            "ml_score": decision.ml_score,
            "risk_tier": decision.risk_tier,
            "action": decision.action,
            "challenge_required": decision.challenge_required,
            "explanation": decision.explanation,
            "latency_ms": round(total_latency_ms, 3),
        }
        self._transactions[txn_id] = record
        self._chronological_txn_ids.append(txn_id)
        if len(self._chronological_txn_ids) > self.MAX_CACHE_SIZE:
            oldest_id = self._chronological_txn_ids.pop(0)
            self._transactions.pop(oldest_id, None)

        return response

    def _persist_evaluation(
        self,
        request: TransactionEvaluateRequest,
        response: TransactionEvaluateResponse,
        decision: Any,
        features: Dict[str, Any],
        rule_infos: List[RuleTriggerInfo],
        db: Optional[Session] = None,
    ) -> None:
        """Internal helper to write User, Transaction, RiskAssessment, and AuditLog."""
        user_hash = hash_identifier(request.user_id)
        masked_user = mask_user_id(request.user_id)
        masked_vpa_str = mask_vpa(request.recipient_vpa)

        def _execute_write(session: Session):
            # 1. Upsert User
            user_repo.get_or_create(session, user_hash=user_hash, masked_display=masked_user)
            user_repo.increment_stats(session, user_hash=user_hash, is_flagged=(response.risk_tier == "HIGH"))

            merchant_cat = getattr(request, "merchant_category", "miscellaneous") or "miscellaneous"

            # 2. Persist Transaction
            txn = Transaction(
                txn_id=response.txn_id,
                user_hash=user_hash,
                amount=response.amount,
                recipient_vpa_masked=masked_vpa_str,
                merchant_category=merchant_cat,
                channel=response.channel,
                device_hash=response.device_hash,
                status=response.status,
                session_id=response.session_id,
                created_at=response.timestamp,
            )

            # 3. Persist Risk Assessment
            assessment = RiskAssessment(
                txn_id=response.txn_id,
                composite_score=response.composite_score,
                ml_score=response.ml_score,
                risk_tier=response.risk_tier,
                action=decision.action,
                challenge_required=response.challenge_required,
                triggered_rules_json=json.dumps([r.model_dump() for r in rule_infos]),
                features_json=json.dumps(features),
                explanation=response.explanation,
                latency_ms=response.latency_ms,
                evaluated_at=response.timestamp,
            )
            transaction_repo.create(session, txn, assessment)

            # 4. Append Tamper-Evident Audit Record
            audit_repo.append_log(
                db=session,
                entity_type="TRANSACTION",
                entity_id=response.txn_id,
                action="EVALUATED",
                actor="RISK_ENGINE",
                details={
                    "user_hash": user_hash,
                    "amount": response.amount,
                    "status": response.status,
                    "risk_tier": response.risk_tier,
                    "composite_score": response.composite_score,
                    "ml_score": response.ml_score,
                    "triggered_rules_count": len(rule_infos),
                },
                timestamp=response.timestamp,
            )

            # 5. Initialize Step-Up OTP challenge if Medium-Risk tier requires verification
            if response.status == "PENDING_VERIFICATION" and response.session_id:
                from app.services.otp_service import otp_service
                otp_service.create_challenge(
                    db=session,
                    txn_id=response.txn_id,
                    user_hash=user_hash,
                    amount=response.amount,
                    recipient_vpa=response.recipient_vpa,
                    custom_session_id=response.session_id,
                    auto_commit=False,
                )

            session.commit()

        with audit_repo.chain_lock:
            try:
                if db is not None:
                    _execute_write(db)
                else:
                    with get_db_context() as session:
                        _execute_write(session)
            except Exception as exc:
                if db is not None:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                logger.error("Failed to persist transaction evaluation: %s", exc, exc_info=True)
                raise PersistenceError(f"Transaction persistence failed: {exc}") from exc

    def get_transaction(self, txn_id: str, db: Optional[Session] = None) -> Optional[Dict]:
        """Retrieve evaluated transaction by ID from memory or database."""
        if txn_id in self._transactions:
            return self._transactions[txn_id]

        if db is not None:
            txn = transaction_repo.get_by_id(db, txn_id)
            if txn:
                return self._txn_to_dict(txn)
        else:
            try:
                with get_db_context() as session:
                    txn = transaction_repo.get_by_id(session, txn_id)
                    if txn:
                        return self._txn_to_dict(txn)
            except Exception:
                pass
        return None

    def list_transactions(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        risk_tier: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[Dict]:
        """List recently evaluated transactions in reverse chronological order.

        Queries SQLite so persistent history across restarts is always preserved,
        while enriching records from the bounded in-memory cache when available.
        """
        user_hash = None
        if user_id:
            is_sha256 = len(user_id) == 64 and all(c in "0123456789abcdef" for c in user_id.lower())
            user_hash = user_id.lower() if is_sha256 else hash_identifier(user_id)

        def _query_db(session: Session) -> List[Dict]:
            txns = transaction_repo.list(
                session,
                limit=limit,
                user_hash=user_hash,
                status=status_filter,
                risk_tier=risk_tier,
            )
            output: List[Dict] = []
            for t in txns:
                cached = self._transactions.get(t.txn_id)
                if cached:
                    # Keep cached status synchronized with DB authoritative state
                    cached["status"] = t.status
                    output.append(cached)
                else:
                    output.append(self._txn_to_dict(t))
            return output

        try:
            if db is not None:
                return _query_db(db)
            with get_db_context() as session:
                return _query_db(session)
        except Exception as exc:
            logger.warning("Database list query failed, falling back to cache: %s", exc)

        # Fallback to in-memory cache
        results = []
        for tid in reversed(self._chronological_txn_ids):
            txn = self._transactions.get(tid)
            if not txn:
                continue
            if user_id is not None and txn.get("user_id") != user_id and txn.get("user_hash") != user_hash:
                continue
            if status_filter is not None and txn.get("status") != status_filter:
                continue
            if risk_tier is not None and txn.get("risk_tier") != risk_tier:
                continue
            results.append(txn)
            if len(results) >= limit:
                break
        return results

    def sync_cache_status(self, txn_id: str, new_status: str) -> None:
        """Synchronize in-memory cached transaction status after external DB commit."""
        if txn_id in self._transactions:
            self._transactions[txn_id]["status"] = new_status

    def update_transaction_status(
        self,
        txn_id: str,
        new_status: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Update transaction status upon subsequent verification."""
        updated = False
        if txn_id in self._transactions:
            self._transactions[txn_id]["status"] = new_status
            updated = True

        def _do_update(session: Session) -> bool:
            ok = transaction_repo.update_status(session, txn_id, new_status)
            if ok:
                audit_repo.append_log(
                    db=session,
                    entity_type="TRANSACTION",
                    entity_id=txn_id,
                    action="STATUS_CHANGE",
                    actor="AUTH_SERVICE",
                    details={"new_status": new_status},
                )
                session.commit()
            return ok

        with audit_repo.chain_lock:
            try:
                if db is not None:
                    updated = _do_update(db) or updated
                else:
                    with get_db_context() as session:
                        updated = _do_update(session) or updated
            except Exception as exc:
                if db is not None:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                logger.error("Failed to update transaction status in database: %s", exc)

        return updated

    def review_transaction(
        self,
        txn_id: str,
        decision: str,
        analyst_note: str = "",
        blacklist_recipient: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute Fraud Analyst manual review decision (APPROVE or REJECT)."""
        normalized = decision.strip().upper()
        if normalized not in {"APPROVE", "REJECT"}:
            raise ValueError("Analyst decision must be 'APPROVE' or 'REJECT'.")

        new_status = "APPROVED" if normalized == "APPROVE" else "REJECTED"

        def _do_review(session: Session) -> Optional[Dict[str, Any]]:
            txn = transaction_repo.get_by_id(session, txn_id)
            if not txn:
                return None

            old_status = txn.status
            txn.status = new_status
            if txn.otp_session and txn.otp_session.status == "ACTIVE":
                txn.otp_session.status = "VERIFIED" if new_status == "APPROVED" else "LOCKED"

            blacklisted_vpa = None
            if normalized == "REJECT" and blacklist_recipient:
                cached = self._transactions.get(txn_id)
                candidate_vpa = (cached.get("recipient_vpa") if cached else None) or txn.recipient_vpa_masked
                if candidate_vpa and "*" not in candidate_vpa and "@" in candidate_vpa:
                    risk_engine_service.add_to_blacklist(
                        candidate_vpa,
                        reason=analyst_note or "Flagged during analyst review",
                        added_by="ANALYST",
                        persist=True,
                        db=session,
                    )
                    blacklisted_vpa = candidate_vpa.strip().lower()
                    audit_repo.append_log(
                        db=session,
                        entity_type="SECURITY_POLICY",
                        entity_id=blacklisted_vpa,
                        action="BLACKLIST_ADDED",
                        actor="ANALYST",
                        details={"source_txn_id": txn_id, "note": analyst_note or "Flagged during analyst review"},
                    )

            audit_repo.append_log(
                db=session,
                entity_type="TRANSACTION",
                entity_id=txn_id,
                action="ANALYST_REVIEW",
                actor="ANALYST",
                details={
                    "old_status": old_status,
                    "new_status": new_status,
                    "decision": normalized,
                    "note": analyst_note or "No remarks provided",
                    "blacklisted_vpa": blacklisted_vpa,
                },
            )
            session.commit()
            self.sync_cache_status(txn_id, new_status)

            result = self._transactions.get(txn_id) or self._txn_to_dict(txn)
            result["status"] = new_status
            return {
                "transaction": result,
                "old_status": old_status,
                "new_status": new_status,
                "blacklisted_vpa": blacklisted_vpa,
            }

        with audit_repo.chain_lock:
            if db is not None:
                return _do_review(db)
            with get_db_context() as session:
                return _do_review(session)

    def clear_records(self):
        """Reset internal storage and clear database tables (for test suite hygiene)."""
        self._transactions.clear()
        self._chronological_txn_ids.clear()
        feature_service.clear_all()
        try:
            from app.services.otp_service import otp_service
            otp_service.clear_failure_cache()
        except Exception:
            pass
        try:
            from app.database.session import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM audit_logs;"))
                conn.execute(text("DELETE FROM risk_assessments;"))
                conn.execute(text("DELETE FROM otp_sessions;"))
                conn.execute(text("DELETE FROM transactions;"))
                conn.execute(text("DELETE FROM users;"))
                conn.commit()
        except Exception:
            pass

    @staticmethod
    def _txn_to_dict(txn: Transaction) -> Dict[str, Any]:
        """Convert SQLAlchemy Transaction model instance to dictionary representation."""
        data = {
            "txn_id": txn.txn_id,
            "user_id": txn.user_hash,
            "user_hash": txn.user_hash,
            "amount": txn.amount,
            "recipient_vpa": txn.recipient_vpa_masked,
            "recipient_vpa_masked": txn.recipient_vpa_masked,
            "timestamp": txn.created_at.isoformat() if txn.created_at else None,
            "created_at": txn.created_at.isoformat() if txn.created_at else None,
            "channel": txn.channel,
            "device_hash": getattr(txn, "device_hash", None),
            "status": txn.status,
            "session_id": txn.session_id,
        }
        if txn.risk_assessment:
            ra = txn.risk_assessment
            assessment_data = {
                "composite_score": ra.composite_score,
                "ml_score": ra.ml_score,
                "risk_tier": ra.risk_tier,
                "action": ra.action,
                "challenge_required": ra.challenge_required,
                "explanation": ra.explanation,
                "latency_ms": ra.latency_ms,
            }
            data.update(assessment_data)
            data["risk_assessment"] = assessment_data
            data["triggered_rules"] = (
                json.loads(ra.triggered_rules_json)
                if ra.triggered_rules_json
                else []
            )
        return data


# Singleton instance for backend runtime
transaction_service = TransactionService()
