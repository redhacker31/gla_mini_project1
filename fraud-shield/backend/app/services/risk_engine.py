"""Composite Risk Decision & Policy Engine.

Evaluates ML anomaly scores, applies deterministic rules, and computes
calibrated Composite Risk Score S(x) across 3 risk tiers. (Expanded in Phase 5).
"""
from app.config import settings


class RiskEngineService:
    """Manages risk tier boundaries and rule blending."""

    def __init__(self):
        self.threshold_low = settings.RISK_THRESHOLD_LOW
        self.threshold_high = settings.RISK_THRESHOLD_HIGH

    def classify_tier(self, score: float) -> str:
        """Map score to LOW, MEDIUM, or HIGH risk tier."""
        if score < self.threshold_low:
            return "LOW"
        elif score < self.threshold_high:
            return "MEDIUM"
        return "HIGH"

