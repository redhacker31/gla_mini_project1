"""Pydantic schemas for Model and Security Rule Explainability."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FeatureAttribution(BaseModel):
    """Marginal contribution of an individual behavioral feature to the ML anomaly score."""
    feature_name: str = Field(..., description="System identifier for the feature")
    feature_label: str = Field(..., description="Human-readable label for dashboard display")
    observed_value: float = Field(..., description="Actual measured feature value")
    baseline_value: float = Field(..., description="Normative baseline value for legitimate transactions")
    attribution_delta: float = Field(..., description="Marginal change in anomaly score (+ pushes to fraud, - pulls to benign)")
    direction: str = Field(..., description="'RISK_INCREASE', 'RISK_DECREASE', or 'NEUTRAL'")
    description: str = Field(..., description="Investigator explanation of the feature's influence")


class RuleAttribution(BaseModel):
    """Outcome and impact of a deterministic domain security rule."""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    triggered: bool = Field(..., description="Whether the rule threshold was breached")
    penalty: float = Field(..., description="Penalty weight added to composite logit")
    severity: str = Field(..., description="'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'")
    reason: str = Field(..., description="Detailed trigger condition and evidence")


class SigmoidDecomposition(BaseModel):
    """Step-by-step mathematical decomposition of logistic sigmoid risk score fusion."""
    base_theta: float = Field(..., description="Calibrated decision threshold offset (-theta)")
    w_ml: float = Field(..., description="ML anomaly score weighting coefficient")
    ml_score: float = Field(..., description="Raw Isolation Forest anomaly score S_ml in [0.0, 1.0]")
    ml_logit_shift: float = Field(..., description="Logit contribution from ML score: w_ml * (S_ml - 0.30)")
    rule_penalties_sum: float = Field(..., description="Arithmetic sum of all triggered domain rule penalties")
    total_logit_z: float = Field(..., description="Fused pre-activation logit z = z_base + z_ml + z_rules")
    composite_score: float = Field(..., description="Final calibrated risk score S(x) = 1 / (1 + exp(-z))")


class ExplainabilityReport(BaseModel):
    """Comprehensive explainability report for security analysts and audit compliance."""
    txn_id: Optional[str] = Field(default=None, description="Transaction ID if referencing a persisted record")
    composite_score: float = Field(..., description="Composite risk score S(x) in [0.0, 1.0]")
    ml_score: float = Field(..., description="Isolation Forest anomaly score S_ml in [0.0, 1.0]")
    risk_tier: str = Field(..., description="'LOW', 'MEDIUM', or 'HIGH'")
    action: str = Field(..., description="'ALLOW', 'CHALLENGE_OTP', or 'FREEZE_REVIEW'")
    challenge_required: bool = Field(..., description="Whether Step-Up authentication challenge is mandated")
    feature_attributions: List[FeatureAttribution] = Field(..., description="Waterfall feature contribution vectors")
    rule_attributions: List[RuleAttribution] = Field(..., description="Evaluated deterministic domain security rules")
    sigmoid_decomposition: SigmoidDecomposition = Field(..., description="Mathematical fusion step-by-step breakdown")
    narrative_summary: str = Field(..., description="Natural language analyst briefing")
    features_snapshot: Dict[str, float] = Field(default_factory=dict, description="Raw feature vector snapshot")
    explanation_latency_ms: float = Field(..., description="Computation time for explainability report")


class WhatIfRequest(BaseModel):
    """Parameters for interactive what-if simulation and sensitivity analysis."""
    amount: float = Field(default=150.0, ge=0.01, le=1000.0, description="Transaction amount in INR")
    txn_count_5m: float = Field(default=0.0, ge=0.0, le=20.0, description="Rolling 5-minute transaction count")
    txn_count_1h: float = Field(default=1.0, ge=0.0, le=100.0, description="Rolling 1-hour transaction count")
    txn_count_24h: float = Field(default=3.0, ge=0.0, le=500.0, description="Rolling 24-hour transaction count")
    amount_sum_5m: float = Field(default=0.0, ge=0.0, description="Rolling 5-minute transaction volume in INR")
    amount_sum_1h: float = Field(default=150.0, ge=0.0, description="Rolling 1-hour transaction volume in INR")
    delta_t_seconds: float = Field(default=86400.0, ge=0.0, description="Time in seconds since prior transaction")
    recipient_entropy_1h: float = Field(default=0.0, ge=0.0, le=5.0, description="Shannon entropy of recipient accounts in 1 hour")
    amount_deviation_ratio: float = Field(default=1.0, ge=0.0, le=50.0, description="Ratio of current amount to historical average")
    recipient_vpa: str = Field(default="kirana_store@upi", description="Destination VPA (checks blacklist)")
    failed_otp_attempts: int = Field(default=0, ge=0, le=5, description="Historical failed OTP attempts on account")
