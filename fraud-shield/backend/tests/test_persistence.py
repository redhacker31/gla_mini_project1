"""Unit and Integration Tests for Phase 7 Persistence and Audit Logging.

Tests cover:
  1. Database engine & table creation.
  2. DPDP Act salted SHA-256 masking.
  3. User repository lifecycle & behavioral metrics.
  4. Transaction & RiskAssessment persistence and relations.
  5. Sequential cryptographic hash-chain audit logging.
  6. Audit tamper-evidence & retroactive modification detection.
  7. Audit API endpoints (/audit/verify, /audit/logs).
  8. End-to-end evaluation latency budget compliance with persistent commit.
"""
from datetime import datetime, timezone
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, init_db
from app.database.session import engine as app_engine, get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.risk_assessment import RiskAssessment
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.audit_repo import audit_repo
from app.repositories.transaction_repo import transaction_repo
from app.repositories.user_repo import user_repo
from app.schemas.transaction import TransactionEvaluateRequest
from app.security.hashing import (
    calculate_audit_hash,
    canonical_iso_timestamp,
    hash_identifier,
    mask_user_id,
    mask_vpa,
)
from app.services.transaction_service import transaction_service


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def ensure_db():
    """Ensure database tables exist and are clean before each test."""
    init_db()
    transaction_service.clear_records()
    yield
    transaction_service.clear_records()


def test_dpdp_hashing_and_masking():
    """Verify non-reversible pseudonymization and display masking."""
    raw_user = "usr_rahul_sharma_987654"
    user_hash1 = hash_identifier(raw_user)
    user_hash2 = hash_identifier(raw_user)

    # Salted hash must be deterministic for the same secret
    assert user_hash1 == user_hash2
    assert len(user_hash1) == 64
    assert raw_user not in user_hash1

    # Masked user display
    masked_user = mask_user_id(raw_user)
    assert masked_user.startswith("usr")
    assert "***" in masked_user

    # Masked VPA
    raw_vpa = "rahul.merchant@okaxis"
    masked_vpa = mask_vpa(raw_vpa)
    assert masked_vpa == "r***t@okaxis"


def test_user_repository_lifecycle():
    """Verify user creation, lookup, and metric incrementation."""
    raw_user = "usr_test_user_persistence_01"
    u_hash = hash_identifier(raw_user)
    masked = mask_user_id(raw_user)

    with sessionmaker(bind=app_engine)() as session:
        # 1. Create or get user
        user = user_repo.get_or_create(session, user_hash=u_hash, masked_display=masked)
        assert user.user_hash == u_hash
        assert user.account_status == "ACTIVE"
        initial_txns = user.total_transactions

        # 2. Increment stats
        user_repo.increment_stats(session, user_hash=u_hash, is_flagged=False)
        session.commit()

        # 3. Verify updated state
        refreshed = user_repo.get_by_hash(session, u_hash)
        assert refreshed is not None
        assert refreshed.total_transactions == initial_txns + 1
        assert refreshed.flagged_count == 0


def test_transaction_and_risk_assessment_persistence():
    """Verify Transaction and RiskAssessment relational persistence."""
    raw_user = "usr_persist_txn_tester_02"
    u_hash = hash_identifier(raw_user)

    req = TransactionEvaluateRequest(
        user_id=raw_user,
        amount=120.0,
        recipient_id="rcp_grocery_44",
        recipient_vpa="grocery44@paytm",
        merchant_category="grocery",
        channel="upi",
    )

    response = transaction_service.evaluate_transaction(req)
    assert response.status in ["APPROVED", "PENDING_VERIFICATION", "SECURITY_FLAGGED"]

    with sessionmaker(bind=app_engine)() as session:
        # Retrieve from database
        persisted_txn = transaction_repo.get_by_id(session, response.txn_id)
        assert persisted_txn is not None
        assert persisted_txn.txn_id == response.txn_id
        assert persisted_txn.amount == 120.0
        assert persisted_txn.user_hash == u_hash
        assert persisted_txn.recipient_vpa_masked == mask_vpa("grocery44@paytm")

        # Check eager-loaded risk assessment
        ra = persisted_txn.risk_assessment
        assert ra is not None
        assert ra.txn_id == response.txn_id
        assert ra.risk_tier == response.risk_tier
        assert round(ra.composite_score, 4) == round(response.composite_score, 4)
        assert ra.latency_ms > 0.0


def test_audit_hash_chain_integrity():
    """Verify that audit records form a cryptographic sequential hash chain."""
    with sessionmaker(bind=app_engine)() as session:
        # Append 3 distinct audit events
        log1 = audit_repo.append_log(
            db=session,
            entity_type="SYSTEM",
            entity_id="SYS_BOOT_01",
            action="BOOTSTRAP",
            actor="SYSTEM",
            details={"version": "1.0.0"},
        )
        session.commit()

        log2 = audit_repo.append_log(
            db=session,
            entity_type="CONFIG",
            entity_id="THRESHOLD_01",
            action="UPDATE",
            actor="ADMIN",
            details={"low": 0.45, "high": 0.80},
        )
        session.commit()

        log3 = audit_repo.append_log(
            db=session,
            entity_type="USER",
            entity_id="USR_HASH_01",
            action="RISK_CHECK",
            actor="ENGINE",
            details={"score": 0.22},
        )
        session.commit()

        # Check linkage: log3.prev_hash == log2.record_hash and log2.prev_hash == log1.record_hash
        assert log3.prev_hash == log2.record_hash
        assert log2.prev_hash == log1.record_hash

        # Run full chain verification
        report = audit_repo.verify_chain_integrity(session)
        assert report["valid"] is True
        assert report["failed_record_id"] is None
        assert report["total_records"] >= 3


def test_tamper_detection_in_audit_chain():
    """Verify that modifying historical audit record contents is immediately detected."""
    with sessionmaker(bind=app_engine)() as session:
        # Create an isolated test record
        tamper_target = audit_repo.append_log(
            db=session,
            entity_type="TRANSACTION",
            entity_id="TXN_TAMPER_TEST",
            action="EVALUATED",
            actor="RISK_ENGINE",
            details={"composite_score": 0.85, "verdict": "SECURITY_FLAGGED"},
        )
        session.commit()
        target_id = tamper_target.id

        # Verification before tampering should be valid
        report_before = audit_repo.verify_chain_integrity(session)
        assert report_before["valid"] is True

        # Maliciously modify the details_json directly in SQL (simulating rogue insider/DB breach)
        record = session.get(AuditLog, target_id)
        assert record is not None
        record.details_json = json.dumps({"composite_score": 0.10, "verdict": "APPROVED"})
        session.commit()

        # Verify integrity detects tampering!
        report_after = audit_repo.verify_chain_integrity(session)
        assert report_after["valid"] is False
        assert report_after["failed_record_id"] == target_id
        assert "Data tampering" in report_after["reason"]

        # Restore genuine record state to keep test DB clean
        genuine_hash = calculate_audit_hash(
            prev_hash=record.prev_hash,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            action=record.action,
            timestamp_str=canonical_iso_timestamp(record.timestamp),
            details_json=json.dumps({"composite_score": 0.85, "verdict": "SECURITY_FLAGGED"}, sort_keys=True, separators=(",", ":")),
        )
        record.details_json = json.dumps({"composite_score": 0.85, "verdict": "SECURITY_FLAGGED"}, sort_keys=True, separators=(",", ":"))
        record.record_hash = genuine_hash
        session.commit()


def test_audit_api_endpoints(client: TestClient):
    """Verify GET /api/v1/transactions/audit/verify and GET /api/v1/transactions/audit/logs."""
    # 1. Audit chain verification endpoint
    resp = client.get("/api/v1/transactions/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "audit_verification" in data
    assert "valid" in data["audit_verification"]

    # 2. Audit logs endpoint
    resp_logs = client.get("/api/v1/transactions/audit/logs?limit=10")
    assert resp_logs.status_code == 200
    logs_data = resp_logs.json()
    assert logs_data["status"] == "success"
    assert isinstance(logs_data["data"], list)


def test_transaction_persistence_latency_sla(client: TestClient):
    """Verify that transaction evaluation with persistent DB commit meets sub-50ms SLA."""
    payload = {
        "user_id": "usr_sla_persistence_bench",
        "amount": 75.0,
        "recipient_id": "rcp_bench_01",
        "recipient_vpa": "vendor@ybl",
        "merchant_category": "food",
        "channel": "upi",
    }

    # Warmup
    client.post("/api/v1/transactions/evaluate", json=payload)

    # Benchmarked run
    resp = client.post("/api/v1/transactions/evaluate", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["latency_ms"] < 50.0  # Must be strictly under sub-50ms SLA
    assert res_data["status"] in ["APPROVED", "PENDING_VERIFICATION"]
