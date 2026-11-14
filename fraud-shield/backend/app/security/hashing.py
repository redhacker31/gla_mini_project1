"""Cryptographic Hashing, PII Masking, and Audit Integrity Primitives.

Adheres to DPDP Act 2023 guidelines:
  - Salted SHA-256 for non-reversible pseudonymization of user identifiers.
  - Partial character masking for display (e.g., in UI / logs).
  - Cryptographic hash-chain generation for tamper-evident audit trails.
"""
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Optional

from app.config import settings


def get_salt() -> str:
    """Return system secret salt for HMAC / SHA-256 pseudonymization."""
    return settings.SECRET_KEY or "fraud-shield-academic-default-salt"


def hash_identifier(identifier: str, salt: Optional[str] = None) -> str:
    """Compute salted SHA-256 digest of a user or recipient identifier.

    Guarantees deterministic pseudonymization across transactions while
    preventing rainbow-table recovery of the original account identifier.
    """
    effective_salt = salt or get_salt()
    data = f"{effective_salt}:{identifier}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def mask_user_id(user_id: str) -> str:
    """Format user identifier into masked display string (e.g. usr_***9921)."""
    if not user_id:
        return "usr_***"
    if len(user_id) <= 6:
        return f"{user_id[:2]}***"
    prefix = user_id[:3]
    suffix = user_id[-4:]
    return f"{prefix}***{suffix}"


def mask_vpa(vpa: str) -> str:
    """Mask a Virtual Payment Address for privacy (e.g. s***e@okaxis)."""
    if not vpa or "@" not in vpa:
        return "***@upi"
    handle, provider = vpa.split("@", 1)
    if len(handle) <= 2:
        masked_handle = handle[0] + "*"
    else:
        masked_handle = f"{handle[0]}***{handle[-1]}"
    return f"{masked_handle}@{provider}"


def canonical_iso_timestamp(dt) -> str:
    """Ensure datetime is converted to canonical UTC ISO string representation."""
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def calculate_audit_hash(
    prev_hash: str,
    entity_type: str,
    entity_id: str,
    action: str,
    timestamp_str: str,
    details_json: str,
) -> str:
    """Compute SHA-256 record hash for append-only audit hash chain.

    H(i) = SHA256(H(i-1) || entity_type || entity_id || action || timestamp || details_json)
    """
    payload = f"{prev_hash}|{entity_type}|{entity_id}|{action}|{timestamp_str}|{details_json}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_otp(otp: str, salt: Optional[str] = None) -> str:
    """Hash a numeric OTP with salt before storing in database."""
    effective_salt = salt or settings.HMAC_SECRET_KEY
    payload = f"{effective_salt}:{otp}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
