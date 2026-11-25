"""Pydantic schemas for Transaction Ingestion and Risk Evaluation."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator
from app.security.sanitization import sanitize_text, validate_amount as sanitize_amount, validate_vpa as sanitize_vpa


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
    device_id: Optional[str] = Field(
        default=None,
        description="Optional client device fingerprint identifier",
        examples=["dev_android_102"],
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        return sanitize_text(v, field_name="user_id", max_length=128)

    @field_validator("recipient_vpa")
    @classmethod
    def validate_vpa(cls, v: str) -> str:
        return sanitize_vpa(v)

    @field_validator("merchant_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return sanitize_text(v, field_name="merchant_category", max_length=64, allow_empty=True)

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        return sanitize_text(v, field_name="channel", max_length=32, allow_empty=True)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = sanitize_text(v, field_name="device_id", max_length=128, allow_empty=True)
        return clean or None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        return sanitize_amount(v)


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
    user_hash: Optional[str] = Field(default=None, description="Salted SHA-256 DPDP identifier")
    amount: float
    recipient_vpa: str
    recipient_vpa_masked: Optional[str] = Field(default=None, description="Masked destination VPA")
    timestamp: datetime
    channel: str
    device_hash: Optional[str] = Field(default=None, description="Salted SHA-256 device fingerprint hash")
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
    user_hash: Optional[str] = None
    amount: float
    recipient_vpa: str
    recipient_vpa_masked: Optional[str] = None
    timestamp: datetime
    channel: str
    device_hash: Optional[str] = Field(default=None, description="Salted SHA-256 device fingerprint hash")
    status: str
    risk_tier: str
    composite_score: float
    ml_score: float
    challenge_required: bool
    session_id: Optional[str] = None
    triggered_rules: List[RuleTriggerInfo] = Field(default_factory=list)
    explanation: str
    latency_ms: float

