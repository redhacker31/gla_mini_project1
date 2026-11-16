"""Security Controls, Gateway Authentication, and Status Endpoints.

Provides endpoints to inspect active security posture, verify HMAC-SHA256 signatures,
and inspect token bucket rate limiting telemetry.
"""
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.security.hmac_auth import (
    generate_gateway_signature,
    require_gateway_signature,
    verify_signature,
)
from app.security.rate_limiter import rate_limiter

router = APIRouter()


class SignatureGenerateRequest(BaseModel):
    """Payload to generate a test HMAC-SHA256 signature."""
    payload: Dict[str, Any] = Field(..., description="JSON payload to sign")
    timestamp: Optional[int] = Field(default=None, description="Optional Unix epoch timestamp")


class SignatureGenerateResponse(BaseModel):
    """Generated HMAC signature details for testing."""
    signature: str
    timestamp: int
    algorithm: str = "HMAC-SHA256"


@router.get(
    "/status",
    summary="Active Security Controls Posture",
    description="Inspect defense-in-depth security layers including Rate Limiter, HMAC Auth, and DPDP Compliance.",
)
async def get_security_posture():
    """Retrieve security configuration and defense-in-depth posture."""
    return {
        "status": "active",
        "rate_limiting": {
            "enabled": settings.RATE_LIMIT_ENABLED,
            "algorithm": "Token Bucket",
            "rate_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            "burst_capacity": settings.RATE_LIMIT_BURST_CAPACITY,
            "exempt_paths": list(rate_limiter.EXEMPT_PREFIXES) if hasattr(rate_limiter, "EXEMPT_PREFIXES") else ["/health", "/docs"],
        },
        "gateway_authentication": {
            "algorithm": "HMAC-SHA256",
            "anti_replay_window_seconds": settings.REPLAY_ATTACK_WINDOW_SECONDS,
            "signature_header": "X-Signature",
            "timestamp_header": "X-Timestamp",
        },
        "http_security_headers": {
            "enabled": settings.SECURITY_HEADERS_ENABLED,
            "x_frame_options": "DENY",
            "x_content_type_options": "nosniff",
            "hsts": "max-age=31536000; includeSubDomains",
            "csp": "Enforced",
        },
        "privacy_compliance": {
            "regulation": "Digital Personal Data Protection (DPDP) Act, 2023",
            "pii_storage": "Zero plaintext mobile numbers or banking credentials",
            "pseudonymization": "Salted SHA-256 with server key derivation",
            "audit_ledger": "Append-Only Cryptographic Hash Chain",
        },
    }


@router.post(
    "/generate-signature",
    response_model=SignatureGenerateResponse,
    summary="Generate HMAC-SHA256 Signature (Testing Helper)",
    description="Generates a valid HMAC-SHA256 signature for a client payload for sandbox testing.",
)
async def generate_test_signature(request: SignatureGenerateRequest) -> SignatureGenerateResponse:
    """Generate signature for a test payload."""
    ts = request.timestamp if request.timestamp is not None else int(time.time())
    body_bytes = json.dumps(request.payload, separators=(",", ":")).encode("utf-8")
    sig = generate_gateway_signature(body=body_bytes, timestamp=ts)
    return SignatureGenerateResponse(
        signature=sig,
        timestamp=ts,
    )


@router.post(
    "/verify-signature",
    summary="Cryptographic HMAC-SHA256 Gateway Signature Test",
    description="Validates that incoming request contains valid X-Signature and X-Timestamp headers.",
)
async def verify_gateway_request(
    auth_data: Dict[str, Any] = Depends(require_gateway_signature),
):
    """Validate authenticated gateway payload."""
    return {
        "status": "authenticated",
        "timestamp": auth_data["timestamp"],
        "signature": auth_data["signature"],
        "message": "HMAC-SHA256 signature verified in constant time. Anti-replay check passed.",
    }
