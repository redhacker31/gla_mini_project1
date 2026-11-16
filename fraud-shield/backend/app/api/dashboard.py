"""Analyst Dashboard & Telemetry API routes."""
from typing import Dict, Any, List
import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.transaction import Transaction
from app.models.risk_assessment import RiskAssessment
from app.models.otp_session import OTPSession
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("/metrics", summary="Live Telemetry Metrics")
async def get_dashboard_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve high-level streaming telemetry metrics from persistent database."""
    # Group status counts via single aggregate query
    status_counts = dict(
        db.query(Transaction.status, func.count(Transaction.txn_id))
        .group_by(Transaction.status)
        .all()
    )
    total_txns = sum(status_counts.values())
    approved_count = status_counts.get("APPROVED", 0)
    challenge_count = status_counts.get("PENDING_VERIFICATION", 0)
    blocked_count = status_counts.get("REJECTED", 0) + status_counts.get("SECURITY_FLAGGED", 0)

    # Group risk tier counts via single aggregate query
    tier_counts = dict(
        db.query(RiskAssessment.risk_tier, func.count(RiskAssessment.id))
        .group_by(RiskAssessment.risk_tier)
        .all()
    )
    low_tier_count = tier_counts.get("LOW", 0)
    med_tier_count = tier_counts.get("MEDIUM", 0)
    high_tier_count = tier_counts.get("HIGH", 0)

    # Rolling latency calculation (bounded to recent 1,000 records for sub-5ms performance)
    latencies = [
        r[0] for r in (
            db.query(RiskAssessment.latency_ms)
            .filter(RiskAssessment.latency_ms.isnot(None))
            .order_by(RiskAssessment.id.desc())
            .limit(1000)
            .all()
        )
    ]
    if latencies:
        p95_latency = float(np.percentile(latencies, 95))
        avg_latency = float(np.mean(latencies))
    else:
        p95_latency = 0.0
        avg_latency = 0.0

    approval_rate = round((approved_count / total_txns * 100), 2) if total_txns > 0 else 100.0
    challenge_rate = round((challenge_count / total_txns * 100), 2) if total_txns > 0 else 0.0
    rejection_rate = round((blocked_count / total_txns * 100), 2) if total_txns > 0 else 0.0

    active_otp_sessions = db.query(OTPSession).filter(OTPSession.status == "ACTIVE").count()
    audit_count = db.query(AuditLog).count()

    return {
        "total_transactions": total_txns,
        "approved_count": approved_count,
        "challenge_count": challenge_count,
        "blocked_count": blocked_count,
        "approval_rate": approval_rate,
        "challenge_rate": challenge_rate,
        "rejection_rate": rejection_rate,
        "p95_latency_ms": round(p95_latency, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "risk_distribution": {
            "low": low_tier_count,
            "medium": med_tier_count,
            "high": high_tier_count,
        },
        "active_otp_sessions": active_otp_sessions,
        "audit_block_height": audit_count,
    }
