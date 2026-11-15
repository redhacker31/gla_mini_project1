"""Pydantic schemas for Step-Up OTP Authentication."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OTPVerifyRequest(BaseModel):
    """Payload to verify an out-of-band Step-Up OTP challenge."""

    session_id: str = Field(
        ...,
        description="Unique verification challenge session ID",
        examples=["otp_sess_a1b2c3d4e5f67890"],
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric verification code",
        examples=["482910"],
    )

    @field_validator("otp")
    @classmethod
    def validate_otp_numeric(cls, v: str) -> str:
        clean = v.strip()
        if not clean.isdigit() or len(clean) != 6:
            raise ValueError("OTP must consist of exactly 6 numeric digits")
        return clean


class OTPVerifyResponse(BaseModel):
    """Result of an OTP verification attempt."""

    success: bool = Field(..., description="Whether OTP verification succeeded")
    status: str = Field(
        ...,
        description="Transaction operational state after verification: APPROVED, PENDING_VERIFICATION, or REJECTED",
        examples=["APPROVED"],
    )
    txn_id: str = Field(..., description="Associated transaction UUID")
    session_id: str = Field(..., description="Challenge session identifier")
    remaining_attempts: int = Field(..., description="Remaining verification attempts before lockout")
    message: str = Field(..., description="Operational status message")


class OTPResendRequest(BaseModel):
    """Request to generate and resend a fresh Step-Up OTP."""

    session_id: str = Field(
        ...,
        description="Active verification challenge session identifier",
        examples=["otp_sess_a1b2c3d4e5f67890"],
    )


class OTPResendResponse(BaseModel):
    """Response returned upon OTP regeneration."""

    success: bool
    session_id: str
    expires_at: datetime
    resends_remaining: int
    message: str


class OTPSessionStatusResponse(BaseModel):
    """Diagnostic state query for an OTP challenge session."""

    session_id: str
    txn_id: str
    status: str
    attempts: int
    max_attempts: int
    resends_used: int
    expires_at: datetime
    phone_masked: Optional[str] = None
    is_expired: bool
