"""HMAC-SHA256 Gateway Authentication & Anti-Replay Verification.

Guarantees message authenticity, payload integrity, and non-repudiation
for incoming banking switch requests.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, Request, status

from app.config import settings


def generate_gateway_signature(
    body: bytes,
    timestamp: int,
    secret_key: Optional[str] = None,
) -> str:
    """Generate canonical HMAC-SHA256 hexadecimal signature for an API payload."""
    key = (secret_key or settings.HMAC_SECRET_KEY).encode("utf-8")
    message = f"{timestamp}.".encode("utf-8") + body
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_signature(
    signature: str,
    timestamp: int,
    body: bytes,
    secret_key: Optional[str] = None,
    max_drift_seconds: Optional[int] = None,
) -> Tuple[bool, str]:
    """Verify HMAC-SHA256 signature and protect against request replay attacks."""
    if not signature:
        return False, "Signature cannot be empty"

    drift_window = max_drift_seconds or settings.REPLAY_ATTACK_WINDOW_SECONDS
    now = int(time.time())

    # Anti-replay timestamp verification
    if abs(now - timestamp) > drift_window:
        return False, f"Request timestamp drift ({abs(now - timestamp)}s) exceeds allowable window ({drift_window}s). Replay rejected."

    # Compute expected signature
    expected_sig = generate_gateway_signature(body=body, timestamp=timestamp, secret_key=secret_key)

    # Constant-time comparison
    if not hmac.compare_digest(expected_sig.lower(), signature.strip().lower()):
        return False, "Cryptographic HMAC signature verification failed. Body or secret mismatch."

    return True, "Signature valid"


async def require_gateway_signature(request: Request) -> Dict[str, Any]:
    """FastAPI route dependency enforcing cryptographic HMAC-SHA256 signature."""
    sig_header = request.headers.get("X-Signature")
    ts_header = request.headers.get("X-Timestamp")

    if not sig_header or not ts_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing mandatory gateway security headers: 'X-Signature' and 'X-Timestamp'.",
        )

    try:
        ts = int(ts_header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 'X-Timestamp' header. Must be integer Unix epoch timestamp in seconds.",
        )

    body = await request.body()
    valid, message = verify_signature(
        signature=sig_header,
        timestamp=ts,
        body=body,
    )

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )

    return {
        "authenticated": True,
        "timestamp": ts,
        "signature": sig_header,
    }


async def require_privileged_auth(request: Request) -> Dict[str, Any]:
    """Enforce either HMAC-SHA256 gateway signature OR constant-time Admin API Key."""
    sig_header = request.headers.get("X-Signature")
    ts_header = request.headers.get("X-Timestamp")
    admin_key = request.headers.get("X-Admin-Key")

    if sig_header and ts_header:
        return await require_gateway_signature(request)

    if admin_key is not None:
        if hmac.compare_digest(admin_key.strip(), settings.ADMIN_API_KEY):
            return {"authenticated": True, "auth_method": "admin_key"}
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid 'X-Admin-Key' credential for privileged security operation.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication headers: provide HMAC ('X-Signature', 'X-Timestamp') or 'X-Admin-Key'.",
    )
