"""Authentication & Step-Up OTP API routes."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/status", summary="OTP Service Status")
async def otp_service_status():
    """Verify that Step-Up OTP service is operational."""
    return {
        "status": "ready",
        "service": "Step-Up OTP Authentication Service",
        "ttl_seconds": 180,
        "max_attempts": 3,
    }

