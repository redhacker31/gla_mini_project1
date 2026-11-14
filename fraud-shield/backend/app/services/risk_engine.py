"""Composite Risk Decision & Policy Engine.

Blends unsupervised ML anomaly scores with deterministic domain security rules
into a calibrated Composite Risk Score S(x) in [0.0, 1.0].
Enforces three operational risk tiers with human-interpretable explanations.
"""
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Set, Tuple
import math
import time
from app.config import settings


@dataclass
class RuleResult:
    """Outcome of a single deterministic security rule evaluation."""
    rule_id: str
    rule_name: str
    triggered: bool
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    penalty: float
    reason: str


@dataclass
class EvaluationDecision:
    """Final operational risk decision emitted by the Composite Risk Engine."""
    composite_score: float
    ml_score: float
    risk_tier: str       # "LOW", "MEDIUM", "HIGH"
    action: str          # "ALLOW", "CHALLENGE_OTP", "FREEZE_REVIEW"
    challenge_required: bool
    triggered_rules: List[Dict]
    explanation: str
    evaluation_latency_ms: float


class RiskEngineService:
    """Composite Risk Decision Engine combining ML inference with domain rules."""

    # Default known malicious/flagged recipient VPAs (simulated cybercrime blacklist)
    DEFAULT_BLACKLIST: Set[str] = {
        "phishing_collect999@upi",
        "attacker_mule4@ybl",
        "fraud_siphon@paytm",
        "scam_qr@oksbi",
        "mule_drainer@ibl",
    }

    def __init__(
        self,
        threshold_low: Optional[float] = None,
        threshold_high: Optional[float] = None,
        w_ml: float = 1.8,
        theta: float = 0.80,
        blacklist: Optional[Set[str]] = None,
    ):
        # Allow dynamic thresholds from config settings
        self.threshold_low = threshold_low if threshold_low is not None else settings.RISK_THRESHOLD_LOW
        self.threshold_high = threshold_high if threshold_high is not None else settings.RISK_THRESHOLD_HIGH
        self.w_ml = w_ml
        self.theta = theta
        self.blacklist = set(blacklist) if blacklist is not None else set(self.DEFAULT_BLACKLIST)

    def add_to_blacklist(self, vpa: str):
        """Register a new malicious VPA to the blacklist."""
        self.blacklist.add(vpa.strip().lower())

    def remove_from_blacklist(self, vpa: str):
        """Remove a VPA from the blacklist."""
        self.blacklist.discard(vpa.strip().lower())

    def evaluate_rules(
        self,
        features: Dict[str, float],
        recipient_vpa: str = "",
        failed_otp_attempts: int = 0,
    ) -> List[RuleResult]:
        """Evaluate deterministic domain rules against transaction features."""
        results: List[RuleResult] = []

        count_5m = float(features.get("txn_count_5m", 0.0))
        delta_t = float(features.get("delta_t_seconds", 86400.0))
        entropy_1h = float(features.get("recipient_entropy_1h", 0.0))
        amt_ratio = float(features.get("amount_deviation_ratio", 1.0))
        amount = float(features.get("amount", 0.0))

        # Rule 1: High Velocity Burst (>= 5 txns in 5 minutes)
        if count_5m >= 5:
            results.append(RuleResult(
                rule_id="RULE_VELOCITY_BURST",
                rule_name="High 5-Minute Velocity Burst",
                triggered=True,
                severity="HIGH",
                penalty=0.65,
                reason=f"Account initiated {int(count_5m)} transactions in the preceding 5 minutes (threshold >= 5).",
            ))
        elif count_5m >= 3:
            results.append(RuleResult(
                rule_id="RULE_VELOCITY_ELEVATED",
                rule_name="Elevated 5-Minute Velocity",
                triggered=True,
                severity="MEDIUM",
                penalty=0.35,
                reason=f"Account initiated {int(count_5m)} transactions in the preceding 5 minutes.",
            ))

        # Rule 2: Rapid-Fire Execution (< 15 seconds between transactions)
        if 0.0 < delta_t < 15.0:
            results.append(RuleResult(
                rule_id="RULE_RAPID_FIRE",
                rule_name="Sub-15s Rapid Execution",
                triggered=True,
                severity="HIGH",
                penalty=0.55,
                reason=f"Inter-arrival delta-t is {delta_t:.1f}s (threshold < 15s indicates automated bot or brute-force).",
            ))
        elif 0.0 < delta_t < 45.0:
            results.append(RuleResult(
                rule_id="RULE_SHORT_INTERVAL",
                rule_name="Short Inter-Arrival Interval",
                triggered=True,
                severity="LOW",
                penalty=0.25,
                reason=f"Inter-arrival delta-t is {delta_t:.1f}s.",
            ))

        # Rule 3: High Recipient Entropy (Fan-out / Smurfing pattern)
        if entropy_1h >= 1.8:
            results.append(RuleResult(
                rule_id="RULE_RECIPIENT_CHURN",
                rule_name="High Recipient Dispersion (Smurfing)",
                triggered=True,
                severity="MEDIUM",
                penalty=0.45,
                reason=f"Recipient Shannon entropy is {entropy_1h:.2f} (threshold >= 1.8 indicates multi-mule dispersion).",
            ))

        # Rule 4: Blacklist Check
        clean_vpa = recipient_vpa.strip().lower()
        if clean_vpa and clean_vpa in self.blacklist:
            results.append(RuleResult(
                rule_id="RULE_BLACKLISTED_RECIPIENT",
                rule_name="Recipient on Fraud Blacklist",
                triggered=True,
                severity="CRITICAL",
                penalty=2.50,
                reason=f"Destination VPA '{recipient_vpa}' matches known mule/fraud syndicate blacklist.",
            ))

        # Rule 5: Extreme Amount Deviation Spike
        if amt_ratio >= 3.5 and amount >= 400.0:
            results.append(RuleResult(
                rule_id="RULE_AMOUNT_SPIKE",
                rule_name="Uncharacteristic Amount Spike",
                triggered=True,
                severity="MEDIUM",
                penalty=0.40,
                reason=f"Transaction value (INR {amount:.2f}) is {amt_ratio:.1f}x the user's historical baseline.",
            ))

        # Rule 6: Repeated Authentication Failure History
        if failed_otp_attempts >= 2:
            results.append(RuleResult(
                rule_id="RULE_REPEATED_AUTH_FAILURES",
                rule_name="Repeated OTP Failures on Account",
                triggered=True,
                severity="HIGH",
                penalty=0.60,
                reason=f"Account has recorded {failed_otp_attempts} consecutive prior authentication failures.",
            ))

        return results

    def compute_composite_score(
        self,
        ml_score: float,
        rules: List[RuleResult],
    ) -> float:
        """Calculate calibrated composite risk score S(x) in [0.0, 1.0] via logistic sigmoid.
        
        Formula:
          z = w_ml * (S_ml - 0.30) + sum(w_i * R_i) - theta
          S(x) = 1 / (1 + exp(-z))
        """
        rule_penalties = sum(r.penalty for r in rules if r.triggered)
        
        # Centering ML score around 0.30 (routine baseline)
        z = self.w_ml * (ml_score - 0.30) + rule_penalties - self.theta

        # Bounded sigmoid evaluation
        try:
            score = 1.0 / (1.0 + math.exp(-z))
        except OverflowError:
            score = 0.0 if z < 0 else 1.0

        return round(float(np_clip(score, 0.0, 1.0)), 4)

    def classify_tier(self, composite_score: float) -> Tuple[str, str, bool]:
        """Map composite score S(x) to risk tier, operational action, and challenge flag.
        
        Tiers:
          - LOW: S(x) < 0.45 -> ALLOW (No challenge)
          - MEDIUM: 0.45 <= S(x) < 0.80 -> CHALLENGE_OTP (Step-Up verification)
          - HIGH: S(x) >= 0.80 -> FREEZE_REVIEW (Freeze transaction and alert)
        """
        if composite_score < self.threshold_low:
            return "LOW", "ALLOW", False
        elif composite_score < self.threshold_high:
            return "MEDIUM", "CHALLENGE_OTP", True
        else:
            return "HIGH", "FREEZE_REVIEW", False

    def generate_explanation(
        self,
        risk_tier: str,
        composite_score: float,
        ml_score: float,
        rules: List[RuleResult],
    ) -> str:
        """Produce human-readable explanation for security analysts and user prompts."""
        triggered = [r for r in rules if r.triggered]
        if risk_tier == "LOW":
            return (
                f"Transaction approved without OTP (Score: {composite_score:.3f}). "
                f"ML behavioral score ({ml_score:.3f}) and velocity indicators are consistent "
                f"with routine legitimate commerce."
            )
        elif risk_tier == "MEDIUM":
            reasons = "; ".join(r.rule_name for r in triggered) if triggered else "Behavioral deviation detected"
            return (
                f"Step-Up SMS OTP required (Score: {composite_score:.3f}). "
                f"Medium risk flagged due to: {reasons}. "
                f"Transaction placed in PENDING_VERIFICATION state."
            )
        else:  # HIGH
            reasons = "; ".join(r.rule_name for r in triggered) if triggered else "Acute behavioral anomaly"
            return (
                f"Transaction BLOCKED & FROZEN for security review (Score: {composite_score:.3f}). "
                f"High risk flagged due to: {reasons}. "
                f"Immediate security notification dispatched to account owner."
            )

    def evaluate(
        self,
        ml_score: float,
        features: Dict[str, float],
        recipient_vpa: str = "",
        failed_otp_attempts: int = 0,
    ) -> EvaluationDecision:
        """Full end-to-end composite evaluation pipeline."""
        t_start = time.perf_counter()

        # 1. Rule checks
        rules = self.evaluate_rules(
            features=features,
            recipient_vpa=recipient_vpa,
            failed_otp_attempts=failed_otp_attempts,
        )

        # 2. Composite score calculation via sigmoid fusion
        composite_score = self.compute_composite_score(ml_score, rules)

        # Hard override: If blacklisted, guarantee HIGH risk tier regardless of other features
        is_blacklisted = any(r.rule_id == "RULE_BLACKLISTED_RECIPIENT" and r.triggered for r in rules)
        if is_blacklisted and composite_score < self.threshold_high:
            composite_score = max(composite_score, 0.85)

        # 3. Classify tier & action
        risk_tier, action, challenge_required = self.classify_tier(composite_score)

        # 4. Generate structured explanation
        explanation = self.generate_explanation(
            risk_tier=risk_tier,
            composite_score=composite_score,
            ml_score=ml_score,
            rules=rules,
        )

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        return EvaluationDecision(
            composite_score=composite_score,
            ml_score=round(float(ml_score), 4),
            risk_tier=risk_tier,
            action=action,
            challenge_required=challenge_required,
            triggered_rules=[asdict(r) for r in rules if r.triggered],
            explanation=explanation,
            evaluation_latency_ms=round(float(latency_ms), 3),
        )


def np_clip(val: float, a_min: float, a_max: float) -> float:
    """Helper clip function."""
    return max(a_min, min(val, a_max))


# Singleton instance for application runtime
risk_engine_service = RiskEngineService()
