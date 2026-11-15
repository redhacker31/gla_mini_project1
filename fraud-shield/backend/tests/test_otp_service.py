"""Unit and Integration Tests for Phase 8 Adaptive Step-Up OTP Authentication.

Tests cover:
  1. Cryptographic 6-digit CSPRNG token generation & salted SHA-256 digests.
  2. Constant-time verification primitives.
  3. Mock SMS gateway dispatch and delivery tracking.
  4. Automatic OTP challenge creation upon Medium-Risk transaction scoring.
  5. Successful OTP verification promoting transaction from PENDING_VERIFICATION to APPROVED.
  6. Anti-brute force attempt counter (3 failed attempts -> session LOCKED, transaction REJECTED).
  7. Expiration rejection after 180s TTL.
  8. Rate-limited resends (max 2 per transaction).
  9. Session status query API and audit trail verification.
"""
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import init_db
from app.database.session import engine as app_engine
from app.main import app
from app.models.otp_session import OTPSession
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.audit_repo import audit_repo
from app.repositories.otp_repo import otp_repo
from app.repositories.transaction_repo import transaction_repo
from app.repositories.user_repo import user_repo
from app.schemas.transaction import TransactionEvaluateRequest
from app.security.hashing import (
    generate_csprng_otp,
    hash_identifier,
    hash_otp,
    verify_otp_hash,
)
from app.services.otp_service import otp_service
from app.services.sms_gateway import sms_gateway
from app.services.transaction_service import transaction_service


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database():
    """Clean database and SMS dispatch ledger before and after each test."""
    init_db()
    transaction_service.clear_records()
    sms_gateway.clear_logs()
    yield
    transaction_service.clear_records()
    sms_gateway.clear_logs()


def test_otp_cryptographic_primitives():
    """Verify CSPRNG 6-digit numeric randomness and constant-time hashing."""
    # 1. Generate 100 OTPs to verify length, numerical format, and randomness
    otps = [generate_csprng_otp() for _ in range(100)]
    for otp in otps:
        assert len(otp) == 6
        assert otp.isdigit()
    assert len(set(otps)) > 90  # High entropy (statistically distinct)

    # 2. Hashing and constant-time comparison
    sample_otp = "582194"
    digest = hash_otp(sample_otp)
    assert len(digest) == 64
    assert sample_otp not in digest

    assert verify_otp_hash(sample_otp, digest) is True
    assert verify_otp_hash("000000", digest) is False
    assert verify_otp_hash("582195", digest) is False


def test_mock_sms_gateway_dispatch():
    """Verify SMS dispatch logging, phone masking, and template construction."""
    phone = "+91 98765 12345"
    otp = "123456"
    amount = 350.0
    vpa = "merchant@upi"
    session_id = "test_sess_01"

    result = sms_gateway.send_otp_sms(
        phone=phone,
        otp=otp,
        amount=amount,
        recipient_vpa=vpa,
        session_id=session_id,
    )

    assert result["status"] == "DELIVERED"
    assert result["phone_masked"].startswith("+91")
    assert result["phone_masked"].endswith("2345")

    dispatch = sms_gateway.get_latest_dispatch(session_id)
    assert dispatch is not None
    assert dispatch["otp"] == otp
    assert "INR 350.00" in dispatch["message"]
    assert vpa in dispatch["message"]


def test_medium_risk_automatically_creates_otp_challenge(client: TestClient):
    """Verify that a Medium-Risk transaction automatically triggers an OTP challenge."""
    # Rapid sequence of 2 payments to trigger RULE_RAPID_FIRE (Medium Risk)
    user_id = "usr_otp_trigger_test_01"
    p1 = {
        "user_id": user_id,
        "amount": 100.0,
        "recipient_vpa": "vendor1@upi",
    }
    client.post("/api/v1/transactions/evaluate", json=p1)

    # Immediate second transaction triggers rapid fire
    p2 = {
        "user_id": user_id,
        "amount": 250.0,
        "recipient_vpa": "vendor2@upi",
    }
    resp = client.post("/api/v1/transactions/evaluate", json=p2)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "PENDING_VERIFICATION"
    assert data["risk_tier"] == "MEDIUM"
    assert data["challenge_required"] is True
    assert data["session_id"] is not None
    assert data["session_id"].startswith("otp_sess_")

    # Verify OTPSession was created in SQLite
    with sessionmaker(bind=app_engine)() as session:
        otp_sess = otp_repo.get_by_id(session, data["session_id"])
        assert otp_sess is not None
        assert otp_sess.status == "ACTIVE"
        assert otp_sess.attempts == 0
        assert otp_sess.txn_id == data["txn_id"]

    # Verify SMS was dispatched
    dispatch = sms_gateway.get_latest_dispatch(data["session_id"])
    assert dispatch is not None
    assert len(dispatch["otp"]) == 6


def test_successful_otp_verification_flow(client: TestClient):
    """Verify valid OTP promotes transaction from PENDING_VERIFICATION to APPROVED."""
    user_id = "usr_otp_verify_success"
    client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 100.0, "recipient_vpa": "merchantA@upi"
    })
    resp = client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 200.0, "recipient_vpa": "merchantB@upi"
    })
    data = resp.json()
    session_id = data["session_id"]
    txn_id = data["txn_id"]

    # Retrieve generated OTP from mock SMS gateway dispatch
    dispatch = sms_gateway.get_latest_dispatch(session_id)
    assert dispatch is not None
    valid_otp = dispatch["otp"]

    # Verify via API: POST /api/v1/auth/verify-otp
    verify_resp = client.post("/api/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": valid_otp,
    })
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["success"] is True
    assert v_data["status"] == "APPROVED"
    assert v_data["txn_id"] == txn_id
    assert "successful" in v_data["message"].lower()

    # Verify transaction status updated in SQLite database
    with sessionmaker(bind=app_engine)() as session:
        txn = transaction_repo.get_by_id(session, txn_id)
        assert txn is not None
        assert txn.status == "APPROVED"

        sess = otp_repo.get_by_id(session, session_id)
        assert sess is not None
        assert sess.status == "VERIFIED"
        assert sess.verified_at is not None

    # Verify audit ledger has VERIFIED entry
    with sessionmaker(bind=app_engine)() as session:
        report = audit_repo.verify_chain_integrity(session)
        assert report["valid"] is True


def test_incorrect_otp_and_lockout_after_max_attempts(client: TestClient):
    """Verify that 3 failed attempts lock session and reject transaction."""
    user_id = "usr_otp_lockout_test"
    client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 100.0, "recipient_vpa": "v1@upi"
    })
    resp = client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 200.0, "recipient_vpa": "v2@upi"
    })
    data = resp.json()
    session_id = data["session_id"]
    txn_id = data["txn_id"]

    # Attempt 1: Wrong OTP
    r1 = client.post("/api/v1/auth/verify-otp", json={"session_id": session_id, "otp": "000000"}).json()
    assert r1["success"] is False
    assert r1["remaining_attempts"] == 2
    assert r1["status"] == "PENDING_VERIFICATION"

    # Attempt 2: Wrong OTP
    r2 = client.post("/api/v1/auth/verify-otp", json={"session_id": session_id, "otp": "111111"}).json()
    assert r2["success"] is False
    assert r2["remaining_attempts"] == 1
    assert r2["status"] == "PENDING_VERIFICATION"

    # Attempt 3: Wrong OTP (Exhausts quota)
    r3 = client.post("/api/v1/auth/verify-otp", json={"session_id": session_id, "otp": "222222"}).json()
    assert r3["success"] is False
    assert r3["remaining_attempts"] == 0
    assert r3["status"] == "REJECTED"
    assert "exceeded" in r3["message"].lower()

    # Verify state in SQLite
    with sessionmaker(bind=app_engine)() as session:
        txn = transaction_repo.get_by_id(session, txn_id)
        assert txn.status == "REJECTED"

        sess = otp_repo.get_by_id(session, session_id)
        assert sess.status == "LOCKED"

        u_hash = hash_identifier(user_id)
        user = user_repo.get_by_hash(session, u_hash)
        assert user.flagged_count > 0


def test_expired_otp_challenge(client: TestClient):
    """Verify that an expired OTP challenge session is rejected."""
    user_id = "usr_otp_expiry_test"
    client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 100.0, "recipient_vpa": "v1@upi"
    })
    resp = client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 200.0, "recipient_vpa": "v2@upi"
    })
    session_id = resp.json()["session_id"]

    # Artificially expire the session by backdating expires_at
    with sessionmaker(bind=app_engine)() as session:
        sess = otp_repo.get_by_id(session, session_id)
        sess.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.commit()

    # Attempt to verify with what would be the valid OTP
    dispatch = sms_gateway.get_latest_dispatch(session_id)
    verify_resp = client.post("/api/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": dispatch["otp"],
    })
    data = verify_resp.json()
    assert data["success"] is False
    assert data["status"] == "EXPIRED"
    assert "expired" in data["message"].lower()


def test_resend_otp_rate_limiting(client: TestClient):
    """Verify rate-limited resend up to maximum 2 times."""
    user_id = "usr_otp_resend_test"
    client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 100.0, "recipient_vpa": "v1@upi"
    })
    resp = client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 200.0, "recipient_vpa": "v2@upi"
    })
    session_id = resp.json()["session_id"]

    # 1st Resend: Allowed (1 remaining)
    r1 = client.post("/api/v1/auth/resend-otp", json={"session_id": session_id})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["success"] is True
    assert d1["resends_remaining"] == 1

    # 2nd Resend: Allowed (0 remaining)
    r2 = client.post("/api/v1/auth/resend-otp", json={"session_id": session_id})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["success"] is True
    assert d2["resends_remaining"] == 0

    # 3rd Resend: Quota exceeded -> 400 Bad Request
    r3 = client.post("/api/v1/auth/resend-otp", json={"session_id": session_id})
    assert r3.status_code == 400
    assert "limit" in r3.json()["detail"].lower()


def test_session_status_query_endpoint(client: TestClient):
    """Verify GET /api/v1/auth/session/{session_id} returns accurate diagnostic state."""
    user_id = "usr_otp_status_query"
    client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 100.0, "recipient_vpa": "v1@upi"
    })
    resp = client.post("/api/v1/transactions/evaluate", json={
        "user_id": user_id, "amount": 200.0, "recipient_vpa": "v2@upi"
    })
    session_id = resp.json()["session_id"]
    txn_id = resp.json()["txn_id"]

    status_resp = client.get(f"/api/v1/auth/session/{session_id}")
    assert status_resp.status_code == 200
    s_data = status_resp.json()
    assert s_data["session_id"] == session_id
    assert s_data["txn_id"] == txn_id
    assert s_data["status"] == "ACTIVE"
    assert s_data["attempts"] == 0
    assert s_data["max_attempts"] == 3
    assert s_data["resends_used"] == 0
    assert s_data["is_expired"] is False
