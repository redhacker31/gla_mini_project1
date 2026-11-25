"""Security Controls, Gateway Authentication, and Status Endpoints.

Provides endpoints to inspect active security posture, verify HMAC-SHA256 signatures,
and inspect token bucket rate limiting telemetry.
"""
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.repositories.audit_repo import audit_repo
from app.security.hmac_auth import (
    generate_gateway_signature,
    require_gateway_signature,
    verify_signature,
)
from app.security.rate_limiter import rate_limiter
from app.security.sanitization import sanitize_text, validate_vpa
from app.services.risk_engine import risk_engine_service

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


class BlacklistVpaRequest(BaseModel):
    """Payload to register a VPA on the active threat blacklist."""
    vpa: str = Field(..., min_length=3, max_length=100, description="VPA handle to blacklist (e.g. fraud_mule@upi)")
    reason: str = Field(default="Analyst threat intelligence registration", max_length=200)


class ThresholdUpdateRequest(BaseModel):
    """Payload to dynamically tune composite risk tier thresholds."""
    threshold_low: float = Field(..., ge=0.10, le=0.75, description="Boundary between LOW and MEDIUM tiers")
    threshold_high: float = Field(..., ge=0.35, le=0.95, description="Boundary between MEDIUM and HIGH tiers")


@router.get(
    "/blacklist",
    summary="List Active Blacklisted VPAs & Risk Thresholds",
    description="Retrieves all currently enforced blacklist VPAs and live operational risk tier thresholds.",
)
async def get_blacklist_and_policy():
    """Retrieve active threat blacklist and composite risk engine policy."""
    return {
        "status": "success",
        "blacklist_count": len(risk_engine_service.blacklist),
        "blacklist": sorted(risk_engine_service.blacklist),
        "thresholds": {
            "low": risk_engine_service.threshold_low,
            "high": risk_engine_service.threshold_high,
        },
    }


@router.post(
    "/blacklist",
    summary="Add Recipient VPA to Blacklist",
    description="Adds a fraudulent VPA to the live Risk Engine blacklist and records an audit event.",
)
async def add_blacklist_vpa(
    payload: BlacklistVpaRequest,
    db: Session = Depends(get_db),
):
    """Register a VPA in the live blacklist."""
    try:
        clean_vpa = validate_vpa(payload.vpa)
        clean_reason = sanitize_text(payload.reason, field_name="reason", max_length=200, allow_empty=True)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    already_present = clean_vpa in risk_engine_service.blacklist
    risk_engine_service.add_to_blacklist(clean_vpa)

    if not already_present:
        audit_repo.append_log(
            db=db,
            entity_type="SECURITY_POLICY",
            entity_id=clean_vpa,
            action="BLACKLIST_ADDED",
            actor="ANALYST",
            details={"vpa": clean_vpa, "reason": clean_reason or "Added via Security Console"},
        )
        db.commit()

    return {
        "status": "success",
        "added": not already_present,
        "vpa": clean_vpa,
        "blacklist": sorted(risk_engine_service.blacklist),
    }


@router.delete(
    "/blacklist/{vpa:path}",
    summary="Remove VPA from Blacklist",
    description="Removes a VPA from the live Risk Engine blacklist and records an audit event.",
)
async def remove_blacklist_vpa(
    vpa: str,
    db: Session = Depends(get_db),
):
    """Remove a VPA from the live blacklist."""
    clean_vpa = vpa.strip().lower()
    if clean_vpa not in risk_engine_service.blacklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPA '{clean_vpa}' is not present in the active blacklist.",
        )

    risk_engine_service.remove_from_blacklist(clean_vpa)
    audit_repo.append_log(
        db=db,
        entity_type="SECURITY_POLICY",
        entity_id=clean_vpa,
        action="BLACKLIST_REMOVED",
        actor="ANALYST",
        details={"vpa": clean_vpa},
    )
    db.commit()

    return {
        "status": "success",
        "removed": clean_vpa,
        "blacklist": sorted(risk_engine_service.blacklist),
    }


@router.patch(
    "/thresholds",
    summary="Tune Operational Risk Thresholds",
    description="Updates LOW/MEDIUM and MEDIUM/HIGH risk score boundaries dynamically in the Risk Engine.",
)
async def update_risk_thresholds(
    payload: ThresholdUpdateRequest,
    db: Session = Depends(get_db),
):
    """Dynamically adjust 3-tier composite risk thresholds."""
    if payload.threshold_low >= payload.threshold_high - 0.05:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold_low must be at least 0.05 below threshold_high.",
        )

    old_low = risk_engine_service.threshold_low
    old_high = risk_engine_service.threshold_high
    risk_engine_service.threshold_low = round(payload.threshold_low, 2)
    risk_engine_service.threshold_high = round(payload.threshold_high, 2)

    audit_repo.append_log(
        db=db,
        entity_type="SECURITY_POLICY",
        entity_id="RISK_THRESHOLDS",
        action="POLICY_UPDATED",
        actor="ANALYST",
        details={
            "old_low": old_low,
            "new_low": risk_engine_service.threshold_low,
            "old_high": old_high,
            "new_high": risk_engine_service.threshold_high,
        },
    )
    db.commit()

    return {
        "status": "success",
        "thresholds": {
            "low": risk_engine_service.threshold_low,
            "high": risk_engine_service.threshold_high,
        },
    }


@router.post(
    "/demo/seed",
    summary="Seed Curated Micro-Transaction Demo Traffic",
    description="Populates a realistic mix of benign UPI payments, a velocity OTP challenge, and a blacklisted mule freeze.",
)
async def seed_demo_traffic():
    """Populate representative Indian micro-transaction traffic for live prototype testing."""
    from app.schemas.simulation import ScenarioType
    from app.services.simulation_service import simulation_service

    routine_batch = simulation_service.trigger_scenario(ScenarioType.ROUTINE, count=4)
    burst_batch = simulation_service.trigger_scenario(ScenarioType.VELOCITY_BURST, count=3)
    blacklist_batch = simulation_service.trigger_scenario(ScenarioType.BLACKLIST_HIT, count=1)

    total = (
        routine_batch.transactions_generated
        + burst_batch.transactions_generated
        + blacklist_batch.transactions_generated
    )
    return {
        "status": "success",
        "seeded_count": total,
        "message": f"Seeded {total} realistic transactions (benign commerce, Step-Up OTP challenge, and threat freeze).",
    }
