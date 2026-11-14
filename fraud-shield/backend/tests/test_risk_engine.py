"""Unit and Boundary Tests for Phase 5 Composite Risk Decision Engine."""
import pytest
from app.services.risk_engine import RiskEngineService, EvaluationDecision


@pytest.fixture
def risk_engine():
    return RiskEngineService(threshold_low=0.45, threshold_high=0.80)


def test_routine_payment_classified_as_low_risk(risk_engine):
    """Verify legitimate routine micro-transactions evaluate to Low Risk tier (< 0.45)."""
    features = {
        "amount": 120.0,
        "txn_count_5m": 0.0,
        "txn_count_1h": 0.0,
        "txn_count_24h": 1.0,
        "delta_t_seconds": 86400.0,
        "recipient_entropy_1h": 0.0,
        "amount_deviation_ratio": 1.05,
    }
    decision = risk_engine.evaluate(
        ml_score=0.22,
        features=features,
        recipient_vpa="groceries_stall@paytm",
    )

    assert isinstance(decision, EvaluationDecision)
    assert decision.composite_score < 0.45, f"Expected Low Risk, got {decision.composite_score}"
    assert decision.risk_tier == "LOW"
    assert decision.action == "ALLOW"
    assert decision.challenge_required is False
    assert len(decision.triggered_rules) == 0
    assert "approved without OTP" in decision.explanation


def test_velocity_burst_triggers_step_up_otp_challenge(risk_engine):
    """Verify velocity bursts evaluate to Medium Risk (0.45 <= S(x) < 0.80) with OTP challenge."""
    features = {
        "amount": 350.0,
        "txn_count_5m": 5.0,  # Velocity burst
        "txn_count_1h": 7.0,
        "txn_count_24h": 10.0,
        "delta_t_seconds": 12.0,  # Rapid fire
        "recipient_entropy_1h": 1.9,  # High recipient churn
        "amount_deviation_ratio": 1.8,
    }
    decision = risk_engine.evaluate(
        ml_score=0.58,
        features=features,
        recipient_vpa="vendor_unknown@ybl",
    )

    assert 0.45 <= decision.composite_score < 0.80, f"Expected Medium Risk, got {decision.composite_score}"
    assert decision.risk_tier == "MEDIUM"
    assert decision.action == "CHALLENGE_OTP"
    assert decision.challenge_required is True
    assert len(decision.triggered_rules) >= 2

    rule_ids = [r["rule_id"] for r in decision.triggered_rules]
    assert "RULE_VELOCITY_BURST" in rule_ids
    assert "RULE_RAPID_FIRE" in rule_ids
    assert "Step-Up SMS OTP required" in decision.explanation


def test_blacklisted_recipient_classified_as_high_risk(risk_engine):
    """Verify blacklisted recipients trigger High Risk tier (>= 0.80) and Freeze action."""
    features = {
        "amount": 200.0,
        "txn_count_5m": 1.0,
        "delta_t_seconds": 3600.0,
        "recipient_entropy_1h": 0.0,
        "amount_deviation_ratio": 1.0,
    }
    decision = risk_engine.evaluate(
        ml_score=0.30,
        features=features,
        recipient_vpa="attacker_mule4@ybl",  # Known blacklisted address
    )

    assert decision.composite_score >= 0.80, f"Expected High Risk, got {decision.composite_score}"
    assert decision.risk_tier == "HIGH"
    assert decision.action == "FREEZE_REVIEW"
    assert decision.challenge_required is False

    rule_ids = [r["rule_id"] for r in decision.triggered_rules]
    assert "RULE_BLACKLISTED_RECIPIENT" in rule_ids
    assert "BLOCKED & FROZEN" in decision.explanation


def test_risk_tier_boundary_conditions(risk_engine):
    """Verify precise mathematical boundaries for Low, Medium, and High tiers."""
    # Low boundary: < 0.45
    tier, action, challenge = risk_engine.classify_tier(0.4499)
    assert tier == "LOW"
    assert action == "ALLOW"
    assert challenge is False

    # Medium lower bound: == 0.45
    tier, action, challenge = risk_engine.classify_tier(0.4500)
    assert tier == "MEDIUM"
    assert action == "CHALLENGE_OTP"
    assert challenge is True

    # Medium upper bound: 0.7999
    tier, action, challenge = risk_engine.classify_tier(0.7999)
    assert tier == "MEDIUM"
    assert action == "CHALLENGE_OTP"
    assert challenge is True

    # High lower bound: >= 0.80
    tier, action, challenge = risk_engine.classify_tier(0.8000)
    assert tier == "HIGH"
    assert action == "FREEZE_REVIEW"
    assert challenge is False

    tier, action, challenge = risk_engine.classify_tier(0.9999)
    assert tier == "HIGH"
    assert action == "FREEZE_REVIEW"


def test_configurable_thresholds():
    """Verify engine adapts immediately to custom threshold calibrations."""
    custom_engine = RiskEngineService(threshold_low=0.35, threshold_high=0.70)
    assert custom_engine.classify_tier(0.34)[0] == "LOW"
    assert custom_engine.classify_tier(0.36)[0] == "MEDIUM"
    assert custom_engine.classify_tier(0.71)[0] == "HIGH"


def test_repeated_otp_failures_penalty(risk_engine):
    """Verify that prior consecutive OTP failures apply rule penalty."""
    features = {
        "amount": 250.0,
        "txn_count_5m": 1.0,
        "delta_t_seconds": 120.0,
        "recipient_entropy_1h": 0.0,
        "amount_deviation_ratio": 1.0,
    }
    # Without failures
    dec1 = risk_engine.evaluate(ml_score=0.40, features=features, failed_otp_attempts=0)
    # With 3 failures
    dec2 = risk_engine.evaluate(ml_score=0.40, features=features, failed_otp_attempts=3)

    assert dec2.composite_score > dec1.composite_score
    rule_ids = [r["rule_id"] for r in dec2.triggered_rules]
    assert "RULE_REPEATED_AUTH_FAILURES" in rule_ids


def test_evaluation_latency(risk_engine):
    """Verify rule evaluation and score fusion completes well within sub-5ms SLA."""
    features = {
        "amount": 490.0,
        "txn_count_5m": 6.0,
        "delta_t_seconds": 10.0,
        "recipient_entropy_1h": 2.0,
        "amount_deviation_ratio": 2.5,
    }
    # Run 500 evaluations
    for _ in range(500):
        dec = risk_engine.evaluate(ml_score=0.65, features=features, recipient_vpa="any@upi")
        assert dec.evaluation_latency_ms < 5.0, f"Latency {dec.evaluation_latency_ms}ms exceeded 5ms"


def test_extreme_velocity_attack_triggers_high_risk_freeze(risk_engine):
    """Verify aggressive multi-mule draining attacks evaluate to High Risk (>= 0.80) and Freeze."""
    features = {
        "amount": 499.0,
        "txn_count_5m": 9.0,
        "txn_count_1h": 15.0,
        "txn_count_24h": 20.0,
        "delta_t_seconds": 8.0,
        "recipient_entropy_1h": 2.4,
        "amount_deviation_ratio": 3.8,
    }
    decision = risk_engine.evaluate(
        ml_score=0.78,
        features=features,
        recipient_vpa="suspicious_mule@ybl",
        failed_otp_attempts=2,
    )

    assert decision.composite_score >= 0.80, f"Expected High Risk, got {decision.composite_score}"
    assert decision.risk_tier == "HIGH"
    assert decision.action == "FREEZE_REVIEW"
    assert decision.challenge_required is False
    assert "BLOCKED & FROZEN" in decision.explanation

