"""Transaction Processing and Orchestration Service.

Coordinates end-to-end transaction evaluation:
  1. Behavioral Feature Extraction (<10ms)
  2. Unsupervised Isolation Forest Anomaly Scoring (<15ms)
  3. Deterministic Security Rules & Sigmoid Score Blending (<5ms)
  4. Decision Mapping (ALLOW, CHALLENGE_OTP, FREEZE_REVIEW)
  5. Audit Storage & Sliding-Window State Management
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional
import time
import uuid

from app.schemas.transaction import (
    RuleTriggerInfo,
    TransactionDetail,
    TransactionEvaluateRequest,
    TransactionEvaluateResponse,
)
from app.services.anomaly_detector import anomaly_detector_service
from app.services.feature_engineering import feature_service
from app.services.risk_engine import risk_engine_service


class TransactionService:
    """Coordinates risk scoring, lifecycle transitions, and transaction records."""

    def __init__(self):
        # In-memory storage for evaluated transactions (precursor to SQLAlchemy persistence in Phase 7)
        self._transactions: Dict[str, Dict] = {}
        self._chronological_txn_ids: List[str] = []

    def evaluate_transaction(self, request: TransactionEvaluateRequest) -> TransactionEvaluateResponse:
        """Execute real-time end-to-end evaluation within sub-50ms latency budget."""
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
            # Generate cryptographic verification session identifier
            session_id = f"otp_sess_{uuid.uuid4().hex[:16]}"
        else:  # FREEZE_REVIEW
            status = "SECURITY_FLAGGED"

        # Record transaction attempt into sliding-window state buffer so subsequent rapid attempts
        # are accurately tracked against velocity thresholds (anti-evasion)
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

        # Store in memory registry
        record = response.model_dump()
        self._transactions[txn_id] = record
        self._chronological_txn_ids.append(txn_id)

        return response

    def get_transaction(self, txn_id: str) -> Optional[Dict]:
        """Retrieve evaluated transaction by ID."""
        return self._transactions.get(txn_id)

    def list_transactions(self, limit: int = 50, user_id: Optional[str] = None) -> List[Dict]:
        """List recently evaluated transactions in reverse chronological order."""
        results = []
        for tid in reversed(self._chronological_txn_ids):
            txn = self._transactions.get(tid)
            if txn:
                if user_id is None or txn.get("user_id") == user_id:
                    results.append(txn)
                if len(results) >= limit:
                    break
        return results

    def update_transaction_status(self, txn_id: str, new_status: str) -> bool:
        """Update transaction status upon subsequent verification (used in Phase 8)."""
        if txn_id in self._transactions:
            self._transactions[txn_id]["status"] = new_status
            return True
        return False

    def clear_records(self):
        """Reset internal storage (for test suite hygiene)."""
        self._transactions.clear()
        self._chronological_txn_ids.clear()


# Singleton instance for backend runtime
transaction_service = TransactionService()
