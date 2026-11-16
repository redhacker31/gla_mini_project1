"""Unit tests for Model & Rule Explainability and What-If Simulation."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.explainability_service import explainability_service
from app.schemas.explainability import WhatIfRequest

client = TestClient(app)


def test_explainability_service_direct():
    """Verify explainability service produces valid feature attributions and sigmoid breakdown."""
    test_features = {
        "amount": 480.0,
        "txn_count_5m": 6.0,
        "txn_count_1h": 8.0,
        "txn_count_24h": 12.0,
        "amount_sum_5m": 1200.0,
        "amount_sum_1h": 2400.0,
        "delta_t_seconds": 12.5,
        "recipient_entropy_1h": 2.14,
        "amount_deviation_ratio": 2.85,
    }

    # Warm-up call to avoid cold-start import overhead
    _ = explainability_service.explain(features=test_features, recipient_vpa="attacker_mule4@ybl")

    report = explainability_service.explain(
        features=test_features,
        recipient_vpa="attacker_mule4@ybl",
        failed_otp_attempts=0,
    )

    assert report.composite_score >= 0.0
    assert report.composite_score <= 1.0
    assert report.risk_tier in ["LOW", "MEDIUM", "HIGH"]
    assert report.action in ["ALLOW", "CHALLENGE_OTP", "FREEZE_REVIEW"]

    # Feature attributions
    assert len(report.feature_attributions) == 9
    feat_names = [f.feature_name for f in report.feature_attributions]
    assert "delta_t_seconds" in feat_names
    assert "txn_count_5m" in feat_names
    assert "recipient_entropy_1h" in feat_names

    # Rule attributions
    triggered = [r for r in report.rule_attributions if r.triggered]
    assert len(triggered) >= 1  # Should trigger rapid-fire or velocity burst

    # Sigmoid decomposition
    sig = report.sigmoid_decomposition
    assert sig.w_ml == 1.8
    assert sig.total_logit_z is not None
    assert round(sig.composite_score, 3) == round(report.composite_score, 3)

    # Narrative text exists and is non-empty
    assert len(report.narrative_summary) > 20
    assert report.explanation_latency_ms < 50.0  # Fast SLA


def test_what_if_api_endpoint():
    """Verify POST /api/v1/explainability/what-if endpoint returns interactive report."""
    payload = {
        "amount": 250.0,
        "txn_count_5m": 1.0,
        "txn_count_1h": 2.0,
        "txn_count_24h": 4.0,
        "amount_sum_5m": 250.0,
        "amount_sum_1h": 400.0,
        "delta_t_seconds": 1200.0,
        "recipient_entropy_1h": 0.0,
        "amount_deviation_ratio": 1.1,
        "recipient_vpa": "kirana_store@upi",
        "failed_otp_attempts": 0,
    }

    response = client.post(f"{settings.API_V1_STR}/explainability/what-if", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "composite_score" in data
    assert "risk_tier" in data
    assert "feature_attributions" in data
    assert len(data["feature_attributions"]) == 9
    assert "rule_attributions" in data
    assert "sigmoid_decomposition" in data
    assert "narrative_summary" in data


def test_explain_transaction_endpoint():
    """Verify POST /api/v1/explainability/explain-transaction endpoint."""
    payload = {
        "user_id": "usr_explain_test_99",
        "amount": 150.0,
        "recipient_vpa": "vendor@upi",
        "merchant_category": "grocery",
        "channel": "UPI_APP",
    }

    response = client.post(f"{settings.API_V1_STR}/explainability/explain-transaction", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["composite_score"] >= 0.0
    assert data["risk_tier"] == "LOW"
    assert data["action"] == "ALLOW"
    assert len(data["feature_attributions"]) == 9


def test_persisted_transaction_explanation():
    """Verify GET /api/v1/explainability/transaction/{txn_id} handles persisted and 404 queries."""
    # First evaluate and persist a transaction
    eval_resp = client.post(
        f"{settings.API_V1_STR}/transactions/evaluate",
        json={
            "user_id": "usr_explain_audit_01",
            "amount": 125.0,
            "recipient_vpa": "store@paytm",
            "merchant_category": "grocery",
            "channel": "UPI_APP",
        },
    )
    assert eval_resp.status_code == 200
    txn_id = eval_resp.json()["txn_id"]

    # Now request explainability report for that persisted transaction
    explain_resp = client.get(f"{settings.API_V1_STR}/explainability/transaction/{txn_id}")
    assert explain_resp.status_code == 200
    data = explain_resp.json()
    assert data["txn_id"] == txn_id
    assert "composite_score" in data
    assert len(data["feature_attributions"]) == 9

    # Test non-existent transaction returns 404
    missing_resp = client.get(f"{settings.API_V1_STR}/explainability/transaction/non-existent-uuid-999")
    assert missing_resp.status_code == 404
