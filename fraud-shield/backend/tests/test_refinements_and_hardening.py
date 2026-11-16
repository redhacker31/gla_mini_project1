"""Unit tests verifying project refinements, memory safety pruning, and edge cases."""
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.security.rate_limiter import Bucket, TokenBucketRateLimiter
from app.services.feature_engineering import FeatureEngineeringService, SlidingWindowBuffer
from app.services.risk_engine import risk_engine_service

client = TestClient(app)


def test_blacklist_coverage_for_presets():
    """Verify that all UI preset blacklist addresses trigger critical Rule 8 block."""
    test_vpas = [
        "blacklisted_mule99@upi",
        "mule_syndicate_01@upi",
        "attacker_mule4@ybl",
        "phishing_collect999@upi",
    ]
    for vpa in test_vpas:
        assert vpa in risk_engine_service.blacklist, f"VPA {vpa} must be in blacklist"
        decision = risk_engine_service.evaluate(
            ml_score=0.1,
            features={
                "amount": 350.0,
                "txn_count_5m": 0.0,
                "txn_count_1h": 0.0,
                "txn_count_24h": 1.0,
                "amount_sum_5m": 0.0,
                "amount_sum_1h": 0.0,
                "delta_t_seconds": 86400.0,
                "recipient_entropy_1h": 0.0,
                "amount_deviation_ratio": 1.0,
            },
            recipient_vpa=vpa,
        )
        assert decision.risk_tier == "HIGH"
        assert decision.action == "FREEZE_REVIEW"
        assert any(r["rule_id"] == "RULE_BLACKLISTED_RECIPIENT" for r in decision.triggered_rules)


def test_rate_limiter_stale_bucket_pruning():
    """Verify that rate limiter prunes stale buckets when capacity threshold is reached."""
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=10)
    now = time.time()

    # Fill limiter with 5002 buckets, half of which are stale (>1h old)
    for i in range(2501):
        limiter._buckets[f"old_ip_{i}"] = Bucket(tokens=10.0, last_update=now - 4000.0)
    for i in range(2501):
        limiter._buckets[f"fresh_ip_{i}"] = Bucket(tokens=10.0, last_update=now)

    assert len(limiter._buckets) > 5000

    # Trigger acquire on a new IP which runs pruning check
    allowed, remaining, _ = limiter.acquire("new_client_ip", tokens=1)
    assert allowed is True
    # Verify stale buckets were purged
    assert len(limiter._buckets) < 3000
    assert "new_client_ip" in limiter._buckets


def test_feature_service_stale_buffer_pruning():
    """Verify that feature engineering service prunes stale user sliding buffers."""
    service = FeatureEngineeringService()
    now = time.time()

    # Inject 10,005 buffers
    for i in range(5005):
        buf = SlidingWindowBuffer()
        # No events -> considered stale
        service._buffers[f"stale_user_{i}"] = buf

    for i in range(5005):
        buf = SlidingWindowBuffer()
        buf.record_transaction(now, 100.0, "store@upi")
        service._buffers[f"active_user_{i}"] = buf

    assert len(service._buffers) > 10000

    # Request buffer for new user, which triggers pruning
    new_buf = service.get_or_create_buffer("fresh_active_user")
    assert new_buf is not None
    # Stale buffers should have been pruned
    assert len(service._buffers) < 9000


def test_dashboard_metrics_aggregation_speed_and_format():
    """Verify optimized dashboard metrics endpoint returns expected schema."""
    resp = client.get(f"{settings.API_V1_STR}/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions" in data
    assert "approved_count" in data
    assert "risk_distribution" in data
    assert "p95_latency_ms" in data
    assert "avg_latency_ms" in data
    assert isinstance(data["risk_distribution"], dict)
    assert "low" in data["risk_distribution"]
    assert "medium" in data["risk_distribution"]
    assert "high" in data["risk_distribution"]
