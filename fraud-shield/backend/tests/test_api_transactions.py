"""Integration and Functional Tests for Phase 6 Transaction Evaluation API."""
import time
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.config import settings
from app.services.transaction_service import transaction_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_storage():
    """Clear transaction records and warm up client before each test."""
    transaction_service.clear_records()
    # Warmup call to load ML libraries into process memory
    client.get(f"{settings.API_V1_STR}/health")
    yield
    transaction_service.clear_records()


def test_evaluate_routine_transaction_low_risk():
    """Verify routine micro-payment evaluates to Low Risk (200 OK, APPROVED, no OTP prompt)."""
    # 1. Warmup call with separate user
    client.post(f"{settings.API_V1_STR}/transactions/evaluate", json={
        "user_id": "usr_warmup_account",
        "amount": 50.00,
        "recipient_vpa": "tea_stall@upi",
    })

    # 2. Legitimate routine payment
    payload = {
        "user_id": "usr_ramesh_village_store",
        "amount": 150.00,
        "recipient_vpa": "kirana_merchant@paytm",
        "channel": "QR_SCAN",
    }
    response = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "txn_id" in data
    assert data["user_id"] == payload["user_id"]
    assert data["amount"] == 150.00
    assert data["recipient_vpa"] == payload["recipient_vpa"]
    assert data["status"] == "APPROVED"
    assert data["risk_tier"] == "LOW"
    assert data["composite_score"] < 0.45
    assert data["challenge_required"] is False
    assert data["session_id"] is None
    assert data["latency_ms"] < 50.0  # Sub-50ms SLA budget
    assert "approved without OTP" in data["explanation"]


def test_evaluate_suspicious_velocity_burst_medium_risk():
    """Verify rapid repeated transfers trigger Medium Risk (PENDING_VERIFICATION, OTP challenged)."""
    user_id = "usr_phishing_victim_01"
    
    # Simulate a burst: 5 preceding transactions in under 2 minutes
    base_payload = {
        "user_id": user_id,
        "amount": 480.00,
        "recipient_vpa": "vendor_mule_1@upi",
        "channel": "UPI_APP",
    }
    # 5 transactions commit into sliding window
    for i in range(5):
        resp = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=base_payload)
        assert resp.status_code == 200

    # 6th transaction within seconds triggers the velocity burst rule
    burst_payload = {
        "user_id": user_id,
        "amount": 490.00,
        "recipient_vpa": "vendor_mule_2@ybl",
        "channel": "UPI_APP",
    }
    response = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=burst_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_tier"] == "MEDIUM"
    assert data["status"] == "PENDING_VERIFICATION"
    assert 0.45 <= data["composite_score"] < 0.80
    assert data["challenge_required"] is True
    assert data["session_id"] is not None
    assert data["session_id"].startswith("otp_sess_")

    rule_ids = [r["rule_id"] for r in data["triggered_rules"]]
    assert "RULE_VELOCITY_BURST" in rule_ids
    assert "Step-Up SMS OTP required" in data["explanation"]


def test_evaluate_blacklisted_recipient_high_risk():
    """Verify blacklisted recipient address triggers High Risk (SECURITY_FLAGGED, frozen)."""
    payload = {
        "user_id": "usr_innocent_account",
        "amount": 250.00,
        "recipient_vpa": "attacker_mule4@ybl",  # Blacklisted
        "channel": "COLLECT_REQUEST",
    }
    response = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_tier"] == "HIGH"
    assert data["status"] == "SECURITY_FLAGGED"
    assert data["composite_score"] >= 0.80
    assert data["challenge_required"] is False
    assert "BLOCKED & FROZEN" in data["explanation"]


def test_evaluate_validation_errors():
    """Verify strict Pydantic input validation (rejects invalid amounts and malformed VPAs)."""
    # 1. Negative amount
    resp1 = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json={
        "user_id": "usr_test",
        "amount": -50.00,
        "recipient_vpa": "valid@upi",
    })
    assert resp1.status_code == 422

    # 2. Zero amount
    resp2 = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json={
        "user_id": "usr_test",
        "amount": 0.00,
        "recipient_vpa": "valid@upi",
    })
    assert resp2.status_code == 422

    # 3. Invalid VPA format (missing '@')
    resp3 = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json={
        "user_id": "usr_test",
        "amount": 100.00,
        "recipient_vpa": "invalid_vpa_without_at_symbol",
    })
    assert resp3.status_code == 422

    # 4. Empty user_id
    resp4 = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json={
        "user_id": "   ",
        "amount": 100.00,
        "recipient_vpa": "valid@upi",
    })
    assert resp4.status_code == 422


def test_list_and_get_transaction_endpoints():
    """Verify GET /transactions and GET /transactions/{txn_id} retrieve evaluations accurately."""
    # Submit 2 transactions
    p1 = {"user_id": "usr_alpha", "amount": 100.0, "recipient_vpa": "merchantA@upi"}
    p2 = {"user_id": "usr_beta", "amount": 200.0, "recipient_vpa": "merchantB@upi"}

    r1 = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=p1).json()
    r2 = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=p2).json()

    txn1_id = r1["txn_id"]
    txn2_id = r2["txn_id"]

    # 1. List transactions
    list_resp = client.get(f"{settings.API_V1_STR}/transactions")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["count"] == 2
    assert list_data["data"][0]["txn_id"] == txn2_id  # Reverse chronological

    # 2. Filter by user_id
    filtered = client.get(f"{settings.API_V1_STR}/transactions?user_id=usr_alpha").json()
    assert filtered["count"] == 1
    assert filtered["data"][0]["user_id"] == "usr_alpha"

    # 3. Get single by ID
    get_resp = client.get(f"{settings.API_V1_STR}/transactions/{txn1_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["txn_id"] == txn1_id

    # 4. Non-existent ID returns 404
    not_found = client.get(f"{settings.API_V1_STR}/transactions/non-existent-uuid")
    assert not_found.status_code == 404


def test_end_to_end_api_latency_budget():
    """Verify round-trip API evaluation complies with the sub-50ms p95 SLA under load."""
    latencies = []
    payload = {
        "user_id": "usr_perf_test",
        "amount": 175.0,
        "recipient_vpa": "fast_merchant@upi",
    }

    # Evaluate 50 transactions
    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.post(f"{settings.API_V1_STR}/transactions/evaluate", json=payload)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        assert resp.status_code == 200

    import numpy as np
    p95_latency = np.percentile(latencies, 95)
    mean_latency = np.mean(latencies)

    print(f"\nAPI Evaluation Latency: Mean = {mean_latency:.2f}ms, p95 = {p95_latency:.2f}ms")
    assert p95_latency < 50.0, f"p95 latency {p95_latency:.2f}ms breached 50ms gateway SLA"
