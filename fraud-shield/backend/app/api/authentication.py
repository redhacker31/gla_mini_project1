"""Authentication & Step-Up OTP API routes.

Provides endpoints to verify, resend, and query out-of-band Step-Up OTP challenge sessions
for digital micro-transactions flagged in the Medium-Risk tier.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.schemas.authentication import (
    OTPResendRequest,
    OTPResendResponse,
    OTPSessionStatusResponse,
    OTPVerifyRequest,
    OTPVerifyResponse,
)
from app.services.otp_service import otp_service
from app.services.transaction_service import transaction_service

router = APIRouter()


@router.get(
    "/status",
    summary="OTP Service Health & Configuration",
    description="Check whether the Step-Up OTP authentication service is operational and inspect policy settings.",
)
async def otp_service_status():
    """Verify that Step-Up OTP service is operational."""
    return {
        "status": "ready",
        "service": "Step-Up OTP Authentication Service",
        "ttl_seconds": settings.OTP_EXPIRY_SECONDS,
        "max_attempts": settings.OTP_MAX_ATTEMPTS,
        "max_resends": settings.OTP_RESEND_MAX,
    }


@router.post(
    "/verify-otp",
    response_model=OTPVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify 6-digit Step-Up OTP",
    description=(
        "Validates candidate 6-digit OTP against stored salted SHA-256 digest in constant time. "
        "Upon success, promotes transaction from PENDING_VERIFICATION to APPROVED. "
        "After 3 consecutive failed attempts, locks session and transitions transaction to REJECTED."
    ),
    responses={
        200: {"description": "OTP verification completed (approved, challenge remaining, or locked/rejected)."},
        400: {"description": "Invalid payload format."},
        404: {"description": "Challenge session not found."},
    },
)
async def verify_otp(
    payload: OTPVerifyRequest,
    db: Session = Depends(get_db),
) -> OTPVerifyResponse:
    """Validate 6-digit OTP challenge."""
    result = otp_service.verify_otp(
        db=db,
        session_id=payload.session_id,
        candidate_otp=payload.otp,
    )

    if result.get("status") == "NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"],
        )

    # Synchronize in-memory cache in transaction_service if updated
    if result.get("status") in ["APPROVED", "REJECTED", "EXPIRED"]:
        transaction_service.update_transaction_status(
            txn_id=result["txn_id"],
            new_status=result["status"],
            db=db,
        )

    return OTPVerifyResponse(
        success=result["success"],
        status=result["status"],
        txn_id=result["txn_id"],
        session_id=result["session_id"],
        remaining_attempts=result["remaining_attempts"],
        message=result["message"],
    )


@router.post(
    "/resend-otp",
    response_model=OTPResendResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend fresh Step-Up OTP",
    description="Regenerates a fresh 6-digit OTP and dispatches via SMS (maximum 2 resends per session).",
    responses={
        200: {"description": "Fresh OTP dispatched successfully."},
        400: {"description": "Resend quota exhausted or invalid state."},
        404: {"description": "Challenge session not found."},
    },
)
async def resend_otp(
    payload: OTPResendRequest,
    db: Session = Depends(get_db),
) -> OTPResendResponse:
    """Regenerate and redispatch Step-Up OTP."""
    result = otp_service.resend_otp(
        db=db,
        session_id=payload.session_id,
    )

    if "not found" in result.get("message", "").lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"],
        )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"],
        )

    return OTPResendResponse(
        success=True,
        session_id=result["session_id"],
        expires_at=result["expires_at"],
        resends_remaining=result["resends_remaining"],
        message=result["message"],
    )


@router.get(
    "/session/{session_id}",
    response_model=OTPSessionStatusResponse,
    summary="Query OTP Challenge Session State",
    description="Inspect remaining attempts, TTL expiration, and lifecycle status for an active challenge.",
    responses={
        200: {"description": "Session found."},
        404: {"description": "Session not found."},
    },
)
async def get_session_status(
    session_id: str,
    db: Session = Depends(get_db),
) -> OTPSessionStatusResponse:
    """Inspect OTP session state."""
    info = otp_service.get_session_status(db=db, session_id=session_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification session '{session_id}' not found.",
        )
    return OTPSessionStatusResponse(**info)


@router.get(
    "/latest-otp/{session_id}",
    summary="Retrieve dispatched OTP (Dev/Sandbox Mode Only)",
    description="Development endpoint to retrieve dispatched OTP for sandbox simulator testing. Disabled in production.",
)
async def get_latest_dispatched_otp(session_id: str):
    """Retrieve dispatched OTP for development testing and interactive UI simulation."""
    if not settings.ENABLE_SANDBOX_OTP_ENDPOINT and (not settings.DEBUG and settings.ENVIRONMENT == "production"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sandbox OTP retrieval disabled in production environment.",
        )
    from app.services.sms_gateway import sms_gateway
    dispatch = sms_gateway.get_latest_dispatch(session_id)
    if not dispatch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No SMS dispatch found for session '{session_id}'.",
        )
    return {
        "session_id": session_id,
        "otp": dispatch["otp"],
        "phone_masked": dispatch["phone_masked"],
        "timestamp": dispatch["timestamp"],
    }
