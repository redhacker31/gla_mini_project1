"""Step-Up OTP Authentication Service.

Generates CSPRNG tokens, manages TTL, and enforces anti-brute force limits.
(Expanded in Phase 8).
"""
from app.config import settings


class OTPService:
    """Manages secure OTP lifecycle and validation."""

    def __init__(self):
        self.ttl = settings.OTP_EXPIRY_SECONDS
        self.max_attempts = settings.OTP_MAX_ATTEMPTS
        self.resend_max = settings.OTP_RESEND_MAX

    def is_active(self) -> bool:
        return True

