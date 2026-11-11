"""Analyst Dashboard & Telemetry API routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/metrics", summary="Live Telemetry Metrics")
async def get_dashboard_metrics():
    """Retrieve high-level streaming telemetry metrics."""
    return {
        "total_transactions": 0,
        "approved_count": 0,
        "challenge_count": 0,
        "blocked_count": 0,
        "p95_latency_ms": 0.0,
        "risk_distribution": {
            "low": 0,
            "medium": 0,
            "high": 0,
        },
    }

