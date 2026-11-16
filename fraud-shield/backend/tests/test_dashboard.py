"""Unit tests for Analyst Dashboard Telemetry endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_dashboard_metrics_endpoint():
    """Verify that /api/v1/dashboard/metrics returns comprehensive telemetry statistics."""
    response = client.get(f"{settings.API_V1_STR}/dashboard/metrics")
    assert response.status_code == 200
    data = response.json()

    # Core count metrics
    assert "total_transactions" in data
    assert "approved_count" in data
    assert "challenge_count" in data
    assert "blocked_count" in data
    assert isinstance(data["total_transactions"], int)
    assert isinstance(data["approved_count"], int)
    assert isinstance(data["challenge_count"], int)
    assert isinstance(data["blocked_count"], int)

    # Percentage rates
    assert "approval_rate" in data
    assert "challenge_rate" in data
    assert "rejection_rate" in data
    assert isinstance(data["approval_rate"], (int, float))

    # Latency percentiles
    assert "p95_latency_ms" in data
    assert "avg_latency_ms" in data
    assert isinstance(data["p95_latency_ms"], (int, float))
    assert isinstance(data["avg_latency_ms"], (int, float))

    # Risk tier distribution breakdown
    assert "risk_distribution" in data
    dist = data["risk_distribution"]
    assert "low" in dist
    assert "medium" in dist
    assert "high" in dist

    # Ledger and OTP counts
    assert "active_otp_sessions" in data
    assert "audit_block_height" in data
    assert isinstance(data["audit_block_height"], int)
