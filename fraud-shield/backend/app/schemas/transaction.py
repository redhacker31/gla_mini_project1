"""Pydantic schemas for Transaction Ingestion and Risk Evaluation."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator


class TransactionEvaluateRequest(BaseModel):
    """Payload submitted by payment gateways or client wallet simulator to evaluate transaction risk."""

    user_id: str = Field(
        ...,
        description="Pseudonymous user identifier or UUIDv4 (DPDP Act compliant)",
        examples=["usr_9b1deb4d3b7d4badac769415e5b8d32c"]
    )
    amount: float = Field(
        ...,
        gt=0.0,
        description="Transaction amount in INR (must be strictly greater than 0.00)",
        examples=[150.00]
    )
    recipient_vpa: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Destination Virtual Payment Address (e.g. merchant@upi or user@okhdfcbank)",
        examples=["kirana_store@paytm"]
    )
    recipient_id: Optional[str] = Field(
        default=None,
        description="Optional recipient account or merchant identifier",
        examples=["rcp_merchant_01"]
    )
    merchant_category: str = Field(
        default="miscellaneous",
        description="Merchant business category (e.g. grocery, food, recharge, p2p, shopping)",
        examples=["grocery"]
    )
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Transaction initiation timestamp (ISO-8601 UTC). Defaults to server current time.",
    )
    channel: str = Field(
        default="UPI_APP",
        description="Transaction origination channel (UPI_APP, QR_SCAN, COLLECT_REQUEST, P2P_INTENT)",
        examples=["QR_SCAN"]
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("user_id cannot be empty or whitespace only")
        return clean

    @field_validator("recipient_vpa")
    @classmethod
    def validate_vpa(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean:
            raise ValueError(f"Invalid VPA handle '{v}'. Must contain '@' (e.g. merchant@upi)")
        return clean

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Transaction amount must be strictly greater than 0.00 INR")
        if v > 100000.0:
            raise ValueError("Amount exceeds maximum single UPI micro/macro transfer limit (INR 100,000)")
        return round(float(v), 2)


class RuleTriggerInfo(BaseModel):
    """Summary of a single rule triggered during evaluation."""
    rule_id: str
    rule_name: str
    severity: str
    penalty: float
    reason: str


class TransactionEvaluateResponse(BaseModel):
    """Evaluation response emitted by the Fraud Shield Gateway within sub-50ms SLA."""

    txn_id: str = Field(..., description="Unique transaction UUID assigned by the gateway")
    user_id: str
    amount: float
    recipient_vpa: str
    timestamp: datetime
    channel: str
    status: str = Field(
        ...,
        description="Operational state: APPROVED, PENDING_VERIFICATION, or SECURITY_FLAGGED",
        examples=["APPROVED"]
    )
    risk_tier: str = Field(
        ...,
        description="Assigned risk tier: LOW, MEDIUM, or HIGH",
        examples=["LOW"]
    )
    composite_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated Composite Risk Score S(x) in [0.0, 1.0]",
        examples=[0.218]
    )
    ml_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Unsupervised Isolation Forest anomaly score S_ml in [0.0, 1.0]",
        examples=[0.195]
    )
    challenge_required: bool = Field(
        ...,
        description="Flag indicating whether out-of-band Step-Up OTP verification is required"
    )
    session_id: Optional[str] = Field(
        None,
        description="Active verification session ID if Step-Up OTP is challenged (Medium Risk)"
    )
    triggered_rules: List[RuleTriggerInfo] = Field(
        default_factory=list,
        description="List of deterministic domain security rules triggered during assessment"
    )
    explanation: str = Field(
        ...,
        description="Human-interpretable decision explanation for analysts and users"
    )
    latency_ms: float = Field(
        ...,
        description="Total gateway evaluation latency in milliseconds (< 50ms SLA)"
    )


class TransactionDetail(BaseModel):
    """Full detail of a recorded transaction."""
    txn_id: str
    user_id: str
    amount: float
    recipient_vpa: str
    timestamp: datetime
    channel: str
    status: str
    risk_tier: str
    composite_score: float
    ml_score: float
    challenge_required: bool
    explanation: str
    latency_ms: float

