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

from app.database.session import get_db_context
from app.models.risk_assessment import RiskAssessment
from app.models.transaction import Transaction
from app.repositories.audit_repo import audit_repo
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


class TransactionService:
    """Coordinates risk scoring, lifecycle transitions, database persistence, and audit logging."""

    def __init__(self):
        # In-memory storage for high-speed cache and backwards-compatibility
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

        # 1. Behavioral Feature Extraction (<10ms SLA)
        features = feature_service.extract_features(
            user_id=request.user_id,
            amount=request.amount,
            timestamp=txn_timestamp,
            recipient_vpa=request.recipient_vpa,
        )
        feature_vector = feature_service.extract_feature_vector(
            user_id=request.user_id,
            amount=request.amount,
            timestamp=txn_timestamp,
            recipient_vpa=request.recipient_vpa,
        )

        # 2. ML Anomaly Detection (<15ms SLA)
        ml_score = anomaly_detector_service.predict_anomaly_score(feature_vector)

        # 3. Composite Risk Engine Decision (<5ms SLA)
        decision = risk_engine_service.evaluate(
            ml_score=ml_score,
            features=features,
            recipient_vpa=request.recipient_vpa,
            failed_otp_attempts=0,
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

        # Record transaction attempt into sliding-window buffer for anti-evasion
        feature_service.commit_transaction(
            user_id=request.user_id,
            amount=request.amount,
            timestamp=txn_timestamp,
            recipient_vpa=request.recipient_vpa,
        )

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
            amount=request.amount,
            recipient_vpa=request.recipient_vpa,
            timestamp=txn_timestamp,
            channel=request.channel,
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

        # In-memory registration
        record = response.model_dump()
        self._transactions[txn_id] = record
        self._chronological_txn_ids.append(txn_id)

        # 5. Database Persistence & Tamper-Evident Audit Logging (Phase 7)
        self._persist_evaluation(
            request=request,
            response=response,
            decision=decision,
            features=features,
            rule_infos=rule_infos,
            db=db,
        )

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
            session.commit()

        try:
            if db is not None:
                _execute_write(db)
            else:
                with get_db_context() as session:
                    _execute_write(session)
        except Exception as exc:
            logger.error("Failed to persist transaction evaluation: %s", exc, exc_info=True)

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
        db: Optional[Session] = None,
    ) -> List[Dict]:
        """List recently evaluated transactions in reverse chronological order."""
        # If in-memory cache has records, return from cache (preserves client-facing user IDs)
        if self._chronological_txn_ids:
            results = []
            for tid in reversed(self._chronological_txn_ids):
                txn = self._transactions.get(tid)
                if txn:
                    if user_id is None or txn.get("user_id") == user_id or txn.get("user_hash") == user_id:
                        results.append(txn)
                    if len(results) >= limit:
                        break
            return results

        # Otherwise query database
        if db is not None:
            user_hash = hash_identifier(user_id) if user_id else None
            txns = transaction_repo.list(db, limit=limit, user_hash=user_hash)
            return [self._txn_to_dict(t) for t in txns]

        try:
            with get_db_context() as session:
                user_hash = hash_identifier(user_id) if user_id else None
                txns = transaction_repo.list(session, limit=limit, user_hash=user_hash)
                if txns:
                    return [self._txn_to_dict(t) for t in txns]
        except Exception:
            pass

        return []

    def update_transaction_status(
        self,
        txn_id: str,
        new_status: str,
        db: Optional[Session] = None,
    ) -> bool:
        """Update transaction status upon subsequent verification (used in Phase 8)."""
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
            return ok

        try:
            if db is not None:
                updated = _do_update(db) or updated
            else:
                with get_db_context() as session:
                    updated = _do_update(session) or updated
        except Exception as exc:
            logger.error("Failed to update transaction status in database: %s", exc)

        return updated

    def clear_records(self):
        """Reset internal storage and clear database tables (for test suite hygiene)."""
        self._transactions.clear()
        self._chronological_txn_ids.clear()
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
            "amount": txn.amount,
            "recipient_vpa": txn.recipient_vpa_masked,
            "timestamp": txn.created_at.isoformat() if txn.created_at else None,
            "channel": txn.channel,
            "status": txn.status,
            "session_id": txn.session_id,
        }
        if txn.risk_assessment:
            ra = txn.risk_assessment
            data.update(
                {
                    "risk_tier": ra.risk_tier,
                    "composite_score": ra.composite_score,
                    "ml_score": ra.ml_score,
                    "challenge_required": ra.challenge_required,
                    "explanation": ra.explanation,
                    "latency_ms": ra.latency_ms,
                    "triggered_rules": (
                        json.loads(ra.triggered_rules_json)
                        if ra.triggered_rules_json
                        else []
                    ),
                }
            )
        return data


# Singleton instance for backend runtime
transaction_service = TransactionService()
