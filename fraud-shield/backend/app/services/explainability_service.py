"""Explainability & Decision Attribution Service for Fraud Shield.

Provides feature-level attributions for the unsupervised Isolation Forest anomaly model,
deterministic security rule auditing, and mathematical decomposition of the logistic sigmoid score fusion.
"""
from typing import Any, Dict, List, Optional, Tuple
import math
import time
import numpy as np

from app.schemas.explainability import (
    ExplainabilityReport,
    FeatureAttribution,
    RuleAttribution,
    SigmoidDecomposition,
    WhatIfRequest,
)
from app.services.anomaly_detector import anomaly_detector_service
from app.services.risk_engine import risk_engine_service, RuleResult


class ExplainabilityService:
    """Computes transparent attribution and what-if simulation reports."""

    # Canonical baseline representing routine legitimate digital micro-commerce
    BENIGN_BASELINES: Dict[str, float] = {
        "amount": 150.0,
        "txn_count_5m": 0.0,
        "txn_count_1h": 1.0,
        "txn_count_24h": 3.0,
        "amount_sum_5m": 0.0,
        "amount_sum_1h": 150.0,
        "delta_t_seconds": 86400.0,
        "recipient_entropy_1h": 0.0,
        "amount_deviation_ratio": 1.0,
    }

    FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
        "amount": {
            "label": "Transaction Amount",
            "unit": "INR",
            "explain_high": "Higher transaction amount increases baseline risk.",
            "explain_low": "Low amount typical of digital micro-commerce.",
        },
        "txn_count_5m": {
            "label": "5-Minute Velocity Count",
            "unit": "txns",
            "explain_high": "Excessive 5-minute frequency indicates rapid velocity or automated script.",
            "explain_low": "Zero or near-zero 5-minute velocity matches normal human behavior.",
        },
        "txn_count_1h": {
            "label": "1-Hour Velocity Count",
            "unit": "txns",
            "explain_high": "High hourly transaction count increases behavioral burst score.",
            "explain_low": "Low hourly frequency consistent with normal daily usage.",
        },
        "txn_count_24h": {
            "label": "24-Hour Velocity Count",
            "unit": "txns",
            "explain_high": "Abnormally high daily volume suggests account sharing or business misuse.",
            "explain_low": "Normal diurnal transaction pacing over 24 hours.",
        },
        "amount_sum_5m": {
            "label": "5-Minute Cumulative Volume",
            "unit": "INR",
            "explain_high": "Rapid aggregate fund outflow in short 5-minute window.",
            "explain_low": "Negligible rapid fund drainage.",
        },
        "amount_sum_1h": {
            "label": "1-Hour Cumulative Volume",
            "unit": "INR",
            "explain_high": "Significant cumulative outflow within 1 hour.",
            "explain_low": "Standard hourly micro-payment total.",
        },
        "delta_t_seconds": {
            "label": "Inter-Arrival Interval (Δt)",
            "unit": "sec",
            "explain_high": "Extremely short inter-arrival interval (<15s) indicates rapid-fire burst.",
            "explain_low": "Spaced inter-arrival interval indicates human-paced transactions.",
        },
        "recipient_entropy_1h": {
            "label": "Recipient Shannon Entropy H(R)",
            "unit": "bits",
            "explain_high": "High entropy indicates multi-mule dispersion or smurfing ring.",
            "explain_low": "Single or concentrated recipient indicates routine repeat merchant.",
        },
        "amount_deviation_ratio": {
            "label": "Amount Deviation Ratio",
            "unit": "x",
            "explain_high": "Substantial deviation from user's historical transaction average.",
            "explain_low": "Transaction amount closely matches user's historical average.",
        },
    }

    # Canonical ordered feature names expected by Isolation Forest pipeline
    ORDERED_FEATURES = [
        "amount",
        "txn_count_5m",
        "txn_count_1h",
        "txn_count_24h",
        "amount_sum_5m",
        "amount_sum_1h",
        "delta_t_seconds",
        "recipient_entropy_1h",
        "amount_deviation_ratio",
    ]

    def _features_to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to 1x9 numpy array in model training order."""
        arr = np.zeros((1, len(self.ORDERED_FEATURES)), dtype=np.float64)
        for idx, feat_name in enumerate(self.ORDERED_FEATURES):
            arr[0, idx] = float(features.get(feat_name, self.BENIGN_BASELINES[feat_name]))
        return arr

    def compute_feature_attributions(
        self,
        features: Dict[str, float],
        observed_ml_score: float,
    ) -> List[FeatureAttribution]:
        """Compute marginal feature attribution deltas against the benign reference baseline."""
        attributions: List[FeatureAttribution] = []
        n_feats = len(self.ORDERED_FEATURES)
        base_vector = self._features_to_array(features)

        # Build batch of 9 perturbed vectors where each feature i is replaced by baseline
        perturbed_batch = np.repeat(base_vector, n_feats, axis=0)
        for idx, feat_name in enumerate(self.ORDERED_FEATURES):
            perturbed_batch[idx, idx] = self.BENIGN_BASELINES[feat_name]

        # Single vectorized inference pass
        scores_without_feature = anomaly_detector_service.predict_anomaly_scores_batch(perturbed_batch)

        for idx, feat_name in enumerate(self.ORDERED_FEATURES):
            meta = self.FEATURE_METADATA.get(feat_name, {"label": feat_name, "unit": ""})
            observed_val = float(features.get(feat_name, self.BENIGN_BASELINES[feat_name]))
            baseline_val = self.BENIGN_BASELINES[feat_name]

            score_without = float(scores_without_feature[idx])
            delta = round(observed_ml_score - score_without, 4)

            # Direction of contribution
            if delta > 0.005:
                direction = "RISK_INCREASE"
                desc = meta.get("explain_high", "Pushes risk score higher.")
            elif delta < -0.005:
                direction = "RISK_DECREASE"
                desc = meta.get("explain_low", "Pulls risk score lower towards baseline.")
            else:
                direction = "NEUTRAL"
                desc = f"Feature is near benign reference ({baseline_val})."

            attributions.append(
                FeatureAttribution(
                    feature_name=feat_name,
                    feature_label=meta["label"],
                    observed_value=round(observed_val, 2),
                    baseline_value=round(baseline_val, 2),
                    attribution_delta=delta,
                    direction=direction,
                    description=desc,
                )
            )

        # Sort feature attributions by magnitude of risk increase (most anomalous first)
        attributions.sort(key=lambda a: a.attribution_delta, reverse=True)
        return attributions

    def audit_rules(
        self,
        features: Dict[str, float],
        recipient_vpa: str,
        failed_otp_attempts: int = 0,
    ) -> List[RuleAttribution]:
        """Audit all deterministic domain security rules, capturing both triggered and inactive rules."""
        active_rules = risk_engine_service.evaluate_rules(
            features=features,
            recipient_vpa=recipient_vpa,
            failed_otp_attempts=failed_otp_attempts,
        )
        active_map = {r.rule_id: r for r in active_rules}

        # Comprehensive rule checklist
        all_rules_catalog = [
            ("RULE_VELOCITY_BURST", "High 5-Minute Velocity Burst", "HIGH", 0.65),
            ("RULE_VELOCITY_ELEVATED", "Elevated 5-Minute Velocity", "MEDIUM", 0.35),
            ("RULE_RAPID_FIRE", "Sub-15s Rapid Execution", "HIGH", 0.55),
            ("RULE_SHORT_INTERVAL", "Short Inter-Arrival Interval", "LOW", 0.25),
            ("RULE_RECIPIENT_CHURN", "High Recipient Dispersion (Smurfing)", "MEDIUM", 0.45),
            ("RULE_BLACKLISTED_RECIPIENT", "Recipient on Fraud Blacklist", "CRITICAL", 2.50),
            ("RULE_AMOUNT_SPIKE", "Uncharacteristic Amount Spike", "MEDIUM", 0.40),
            ("RULE_REPEATED_AUTH_FAILURES", "Repeated OTP Failures on Account", "HIGH", 0.60),
        ]

        attributions: List[RuleAttribution] = []
        for r_id, r_name, r_sev, r_pen in all_rules_catalog:
            if r_id in active_map:
                active_res = active_map[r_id]
                attributions.append(
                    RuleAttribution(
                        rule_id=r_id,
                        rule_name=r_name,
                        triggered=True,
                        penalty=active_res.penalty,
                        severity=active_res.severity,
                        reason=active_res.reason,
                    )
                )
            else:
                attributions.append(
                    RuleAttribution(
                        rule_id=r_id,
                        rule_name=r_name,
                        triggered=False,
                        penalty=0.0,
                        severity=r_sev,
                        reason="Rule conditions not breached.",
                    )
                )

        # Sort so triggered rules appear first
        attributions.sort(key=lambda r: (not r.triggered, -r.penalty))
        return attributions

    def decompose_sigmoid(
        self,
        ml_score: float,
        rules: List[RuleAttribution],
    ) -> SigmoidDecomposition:
        """Decompose logistic sigmoid fusion into explicit arithmetic components."""
        theta = risk_engine_service.theta
        w_ml = risk_engine_service.w_ml

        # Shift ML score relative to 0.30 routine baseline
        ml_logit_shift = w_ml * (ml_score - 0.30)
        rule_penalties_sum = sum(r.penalty for r in rules if r.triggered)

        total_logit_z = -theta + ml_logit_shift + rule_penalties_sum

        try:
            composite_score = 1.0 / (1.0 + math.exp(-total_logit_z))
        except OverflowError:
            composite_score = 0.0 if total_logit_z < 0 else 1.0

        return SigmoidDecomposition(
            base_theta=round(-theta, 4),
            w_ml=round(w_ml, 2),
            ml_score=round(ml_score, 4),
            ml_logit_shift=round(ml_logit_shift, 4),
            rule_penalties_sum=round(rule_penalties_sum, 4),
            total_logit_z=round(total_logit_z, 4),
            composite_score=round(composite_score, 4),
        )

    def generate_narrative_summary(
        self,
        risk_tier: str,
        composite_score: float,
        ml_score: float,
        feature_attributions: List[FeatureAttribution],
        rule_attributions: List[RuleAttribution],
        recipient_vpa: str,
    ) -> str:
        """Generate executive natural-language briefing for fraud analysts and compliance."""
        triggered_rules = [r for r in rule_attributions if r.triggered]
        top_risk_features = [f for f in feature_attributions if f.direction == "RISK_INCREASE"][:2]

        if risk_tier == "LOW":
            return (
                f"Transaction evaluated as LOW RISK (Composite Score: {composite_score:.3f} < 0.45). "
                f"The Isolation Forest model classified the behavioral feature vector as typical routine micro-commerce "
                f"(S_ml={ml_score:.3f}). Zero security rule violations were triggered. Auto-approved with sub-50ms SLA."
            )
        elif risk_tier == "MEDIUM":
            rule_names = ", ".join(r.rule_name for r in triggered_rules) if triggered_rules else "Elevated behavioral anomaly"
            feat_drivers = ", ".join(f"{f.feature_label} ({f.observed_value})" for f in top_risk_features)
            return (
                f"Transaction flagged as MEDIUM RISK (Composite Score: {composite_score:.3f}, within [0.45, 0.80)). "
                f"Requires Step-Up OTP challenge (180s TTL). Primary risk drivers: {feat_drivers or 'pacing deviation'}. "
                f"Triggered deterministic rules: {rule_names}."
            )
        else:  # HIGH
            rule_names = ", ".join(r.rule_name for r in triggered_rules) if triggered_rules else "Severe anomaly"
            feat_drivers = ", ".join(f"{f.feature_label} ({f.observed_value})" for f in top_risk_features)
            return (
                f"Transaction BLOCKED as HIGH RISK (Composite Score: {composite_score:.3f} >= 0.80). "
                f"Transaction frozen and flagged for immediate security review. "
                f"Critical threats detected: {rule_names}. Behavioral drivers: {feat_drivers or 'acute anomaly'}."
            )

    def explain(
        self,
        features: Dict[str, float],
        recipient_vpa: str = "kirana_store@upi",
        failed_otp_attempts: int = 0,
        txn_id: Optional[str] = None,
    ) -> ExplainabilityReport:
        """Generate comprehensive explainability report for any transaction feature set."""
        start_time = time.perf_counter()

        # 1. Feature array and ML anomaly score
        feat_array = self._features_to_array(features)
        ml_score = anomaly_detector_service.predict_anomaly_score(feat_array)

        # 2. Feature attributions
        feature_attributions = self.compute_feature_attributions(features, ml_score)

        # 3. Rule audit
        rule_attributions = self.audit_rules(features, recipient_vpa, failed_otp_attempts)

        # 4. Sigmoid fusion decomposition
        sigmoid_decomp = self.decompose_sigmoid(ml_score, rule_attributions)
        composite_score = sigmoid_decomp.composite_score

        # 5. Risk tier classification
        risk_tier, action, challenge_required = risk_engine_service.classify_tier(composite_score)

        # 6. Natural language narrative
        narrative = self.generate_narrative_summary(
            risk_tier=risk_tier,
            composite_score=composite_score,
            ml_score=ml_score,
            feature_attributions=feature_attributions,
            rule_attributions=rule_attributions,
            recipient_vpa=recipient_vpa,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return ExplainabilityReport(
            txn_id=txn_id,
            composite_score=composite_score,
            ml_score=ml_score,
            risk_tier=risk_tier,
            action=action,
            challenge_required=challenge_required,
            feature_attributions=feature_attributions,
            rule_attributions=rule_attributions,
            sigmoid_decomposition=sigmoid_decomp,
            narrative_summary=narrative,
            features_snapshot={k: float(features.get(k, 0.0)) for k in self.ORDERED_FEATURES},
            explanation_latency_ms=round(latency_ms, 2),
        )

    def what_if_analysis(self, req: WhatIfRequest) -> ExplainabilityReport:
        """Run rapid sensitivity simulation with modified parameters."""
        features = {
            "amount": req.amount,
            "txn_count_5m": req.txn_count_5m,
            "txn_count_1h": req.txn_count_1h,
            "txn_count_24h": req.txn_count_24h,
            "amount_sum_5m": req.amount_sum_5m,
            "amount_sum_1h": req.amount_sum_1h,
            "delta_t_seconds": req.delta_t_seconds,
            "recipient_entropy_1h": req.recipient_entropy_1h,
            "amount_deviation_ratio": req.amount_deviation_ratio,
        }
        return self.explain(
            features=features,
            recipient_vpa=req.recipient_vpa,
            failed_otp_attempts=req.failed_otp_attempts,
            txn_id="sim_what_if",
        )


# Singleton instance
explainability_service = ExplainabilityService()
