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


def test_analyst_review_override_and_audit():
    """Verify privileged auth enforcement and analyst manual review transitions + audit record."""
    eval_resp = client.post(
        f"{settings.API_V1_STR}/transactions/evaluate",
        json={
            "user_id": "usr_review_test",
            "amount": 350.0,
            "recipient_vpa": "blacklisted_mule99@upi",
            "merchant_category": "p2p",
            "channel": "UPI_APP",
        },
    )
    assert eval_resp.status_code == 200
    txn_id = eval_resp.json()["txn_id"]
    assert eval_resp.json()["status"] == "SECURITY_FLAGGED"

    # Unauthenticated review must be rejected (401)
    unauth_resp = client.post(
        f"{settings.API_V1_STR}/transactions/{txn_id}/review",
        json={"decision": "APPROVE", "analyst_note": "No key"},
    )
    assert unauth_resp.status_code == 401

    # Invalid Admin Key must be rejected (403)
    bad_resp = client.post(
        f"{settings.API_V1_STR}/transactions/{txn_id}/review",
        headers={"X-Admin-Key": "wrong-key"},
        json={"decision": "APPROVE", "analyst_note": "Wrong key"},
    )
    assert bad_resp.status_code == 403

    # Override to APPROVED via authorized analyst review
    rev_resp = client.post(
        f"{settings.API_V1_STR}/transactions/{txn_id}/review",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
        json={"decision": "APPROVE", "analyst_note": "Verified customer callback"},
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["data"]["status"] == "APPROVED"

    # Confirm persisted status via GET
    get_resp = client.get(f"{settings.API_V1_STR}/transactions/{txn_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["status"] == "APPROVED"


def test_dynamic_blacklist_and_threshold_policy():
    """Verify live blacklist management and adaptive threshold updates with auth."""
    test_vpa = "temp_fraud_test99@upi"
    orig_low = risk_engine_service.threshold_low
    orig_high = risk_engine_service.threshold_high
    auth_headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    try:
        # 1. Unauthenticated mutation rejected (401)
        unauth_add = client.post(
            f"{settings.API_V1_STR}/system/security/blacklist",
            json={"vpa": test_vpa, "reason": "No auth"},
        )
        assert unauth_add.status_code == 401

        # 2. Add VPA to blacklist with auth
        add_resp = client.post(
            f"{settings.API_V1_STR}/system/security/blacklist",
            headers=auth_headers,
            json={"vpa": test_vpa, "reason": "Automated unit test"},
        )
        assert add_resp.status_code == 200
        assert test_vpa in add_resp.json()["blacklist"]

        # 3. Verify GET returns VPA
        list_resp = client.get(f"{settings.API_V1_STR}/system/security/blacklist")
        assert list_resp.status_code == 200
        assert test_vpa in list_resp.json()["blacklist"]

        # 4. Remove VPA from blacklist
        del_resp = client.delete(
            f"{settings.API_V1_STR}/system/security/blacklist/{test_vpa}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 200
        assert test_vpa not in del_resp.json()["blacklist"]

        # 5. Tune thresholds and verify /health reflects live values
        patch_resp = client.patch(
            f"{settings.API_V1_STR}/system/security/thresholds",
            headers=auth_headers,
            json={"threshold_low": 0.40, "threshold_high": 0.75},
        )
        assert patch_resp.status_code == 200
        health_resp = client.get(f"{settings.API_V1_STR}/health")
        assert health_resp.json()["risk_thresholds"]["low"] == 0.40
        assert health_resp.json()["risk_thresholds"]["high"] == 0.75
    finally:
        risk_engine_service.remove_from_blacklist(test_vpa)
        risk_engine_service.update_thresholds(orig_low, orig_high)


def test_demo_seed_and_filtered_transaction_list():
    """Verify curated demo seed endpoint and risk_tier query filtering."""
    seed_resp = client.post(f"{settings.API_V1_STR}/system/security/demo/seed")
    assert seed_resp.status_code == 200
    assert seed_resp.json()["seeded_count"] >= 8

    high_resp = client.get(f"{settings.API_V1_STR}/transactions?risk_tier=HIGH&limit=20")
    assert high_resp.status_code == 200
    high_data = high_resp.json()["data"]
    assert len(high_data) >= 1
    assert all(item["risk_tier"] == "HIGH" for item in high_data)


def test_concurrent_evaluation_preserves_audit_chain_integrity():
    """Verify parallel transaction evaluations never fork the SHA-256 audit hash chain."""
    from concurrent.futures import ThreadPoolExecutor
    from app.database.session import get_db_context
    from app.repositories.audit_repo import audit_repo
    from app.schemas.transaction import TransactionEvaluateRequest
    from app.services.transaction_service import transaction_service

    transaction_service.clear_records()

    def _run_one(i: int):
        req = TransactionEvaluateRequest(
            user_id=f"usr_conc_chain_{i % 5}",
            amount=round(50.0 + (i * 10.0) % 400.0, 2),
            recipient_vpa=f"merchant_{i % 3}@upi",
            channel="UPI_APP",
            device_id=f"dev_conc_{i % 2}",
        )
        return transaction_service.evaluate_transaction(req)

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(_run_one, range(24)))

    assert len(results) == 24
    with get_db_context() as session:
        integrity = audit_repo.verify_chain_integrity(session)
        assert integrity["valid"] is True, integrity.get("reason")
        assert integrity["total_records"] >= 24


def test_policy_persistence_and_sliding_window_hydration():
    """Verify blacklist, thresholds, and 24h sliding windows survive simulated server restarts."""
    from app.services.feature_engineering import feature_service
    from app.services.transaction_service import transaction_service

    transaction_service.clear_records()
    persisted_vpa = "restart_survive_mule@upi"
    orig_low = risk_engine_service.threshold_low
    orig_high = risk_engine_service.threshold_high
    auth_headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    try:
        # 1. Persist blacklist & thresholds via API
        assert client.post(
            f"{settings.API_V1_STR}/system/security/blacklist",
            headers=auth_headers,
            json={"vpa": persisted_vpa, "reason": "Restart persistence test"},
        ).status_code == 200
        assert client.patch(
            f"{settings.API_V1_STR}/system/security/thresholds",
            headers=auth_headers,
            json={"threshold_low": 0.42, "threshold_high": 0.78},
        ).status_code == 200

        # 2. Record 2 transactions for a user
        user_id = "usr_restart_hydrator_01"
        for amt in (100.0, 120.0):
            r = client.post(
                f"{settings.API_V1_STR}/transactions/evaluate",
                json={"user_id": user_id, "amount": amt, "recipient_vpa": "kirana@upi", "device_id": "dev_restart_1"},
            )
            assert r.status_code == 200

        # 3. Wipe in-memory state to simulate process restart
        risk_engine_service.blacklist.clear()
        risk_engine_service.threshold_low = 0.99
        risk_engine_service.threshold_high = 0.99
        feature_service.clear_all()

        # 4. Run startup reload/hydration
        risk_engine_service.load_policies_from_db()
        hydrated_count = feature_service.hydrate_from_db()

        assert hydrated_count >= 2
        assert persisted_vpa in risk_engine_service.blacklist
        assert risk_engine_service.threshold_low == 0.42
        assert risk_engine_service.threshold_high == 0.78

        feats = feature_service.extract_features(user_id=user_id, amount=110.0, recipient_vpa="kirana@upi")
        assert feats["txn_count_24h"] >= 2.0
    finally:
        risk_engine_service.remove_from_blacklist(persisted_vpa)
        risk_engine_service.update_thresholds(orig_low, orig_high)


def test_device_fingerprinting_and_otp_failure_rules():
    """Verify RULE_NEW_OR_SHARED_DEVICE and RULE_REPEATED_AUTH_FAILURES trigger in live evaluation."""
    from app.services.sms_gateway import sms_gateway
    from app.services.transaction_service import transaction_service

    transaction_service.clear_records()
    sms_gateway.clear_logs()
    user_id = "usr_device_otp_tester"

    # 1. Establish initial known device
    r1 = client.post(
        f"{settings.API_V1_STR}/transactions/evaluate",
        json={
            "user_id": user_id,
            "amount": 100.0,
            "recipient_vpa": "shop1@upi",
            "device_id": "dev_trusted_phone",
        },
    )
    assert r1.status_code == 200
    assert r1.json()["device_hash"] is not None

    # 2. Switch to unseen device -> triggers RULE_NEW_OR_SHARED_DEVICE
    r2 = client.post(
        f"{settings.API_V1_STR}/transactions/evaluate",
        json={
            "user_id": user_id,
            "amount": 120.0,
            "recipient_vpa": "shop1@upi",
            "device_id": "dev_unseen_emulator",
        },
    )
    assert r2.status_code == 200
    r2_data = r2.json()
    assert any(rule["rule_id"] == "RULE_NEW_OR_SHARED_DEVICE" for rule in r2_data["triggered_rules"])
    assert r2_data["challenge_required"] is True
    sess_id = r2_data["session_id"]
    assert sess_id is not None

    # 3. Fail OTP verification twice -> populates historical failure signal
    for _ in range(2):
        bad_verify = client.post(
            f"{settings.API_V1_STR}/auth/verify-otp",
            json={"session_id": sess_id, "otp": "000000"},
        )
        assert bad_verify.status_code == 200
        assert bad_verify.json()["success"] is False

    # 4. Next transaction for same user triggers RULE_REPEATED_AUTH_FAILURES
    r3 = client.post(
        f"{settings.API_V1_STR}/transactions/evaluate",
        json={
            "user_id": user_id,
            "amount": 130.0,
            "recipient_vpa": "shop1@upi",
            "device_id": "dev_trusted_phone",
        },
    )
    assert r3.status_code == 200
    assert any(rule["rule_id"] == "RULE_REPEATED_AUTH_FAILURES" for rule in r3.json()["triggered_rules"])


def test_micro_transaction_limit_and_production_otp_gate():
    """Verify RULE_MICRO_TXN_LIMIT_EXCEEDED (>= INR 1,000) and production sandbox OTP lock."""
    from app.config import Settings

    # 1. Production Settings automatically disable sandbox OTP retrieval unless explicitly set
    prod_settings = Settings(ENVIRONMENT="production")
    assert prod_settings.ENABLE_SANDBOX_OTP_ENDPOINT is False

    override_settings = Settings(ENVIRONMENT="production", ENABLE_SANDBOX_OTP_ENDPOINT=True)
    assert override_settings.ENABLE_SANDBOX_OTP_ENDPOINT is True

    # 2. Live /latest-otp returns 403 when sandbox endpoint is disabled
    orig_sandbox = settings.ENABLE_SANDBOX_OTP_ENDPOINT
    try:
        settings.ENABLE_SANDBOX_OTP_ENDPOINT = False
        forbidden_resp = client.get(f"{settings.API_V1_STR}/auth/latest-otp/otp_sess_nonexistent")
        assert forbidden_resp.status_code == 403
    finally:
        settings.ENABLE_SANDBOX_OTP_ENDPOINT = orig_sandbox

    # 3. Bypassing frontend max="999.99" triggers RULE_MICRO_TXN_LIMIT_EXCEEDED
    over_limit = client.post(
        f"{settings.API_V1_STR}/transactions/evaluate",
        json={
            "user_id": "usr_over_limit_test",
            "amount": 1500.00,
            "recipient_vpa": "normal_store@upi",
        },
    )
    assert over_limit.status_code == 200
    data = over_limit.json()
    assert data["risk_tier"] == "HIGH"
    assert data["status"] == "SECURITY_FLAGGED"
    assert any(r["rule_id"] == "RULE_MICRO_TXN_LIMIT_EXCEEDED" for r in data["triggered_rules"])
