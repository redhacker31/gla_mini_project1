"""Unit and Integration Tests for Security Hardening, Rate Limiting, and Input Sanitization."""
import json
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.security.hmac_auth import generate_gateway_signature
from app.security.rate_limiter import rate_limiter

client = TestClient(app)


def setup_function():
    """Reset rate limiter before each test."""
    rate_limiter.reset()


def test_security_response_headers():
    """Verify that all HTTP responses include OWASP recommended defense-in-depth security headers."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    headers = response.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Strict-Transport-Security" in headers
    assert "Content-Security-Policy" in headers


def test_token_bucket_rate_limiter_throttling():
    """Verify that token bucket throttles burst traffic and returns HTTP 429 with Retry-After header."""
    rate_limiter.reset()
    # Consume all available burst capacity (40 tokens)
    allowed_count = 0
    blocked_count = 0

    for i in range(settings.RATE_LIMIT_BURST_CAPACITY + 10):
        resp = client.get(
            f"{settings.API_V1_STR}/dashboard/metrics",
            headers={"X-Forwarded-For": "198.51.100.42"},
        )
        if resp.status_code == 200:
            allowed_count += 1
            assert "X-RateLimit-Limit" in resp.headers
        elif resp.status_code == 429:
            blocked_count += 1
            assert "Retry-After" in resp.headers
            assert "Rate limit exceeded" in resp.json()["detail"]

    assert allowed_count >= settings.RATE_LIMIT_BURST_CAPACITY
    assert blocked_count >= 5

    # Cleanup
    rate_limiter.reset()


def test_sql_injection_defense():
    """Verify that SQL injection payloads in user identifiers or fields are blocked."""
    sqli_payloads = [
        "admin' OR '1'='1",
        "user_123; DROP TABLE users;--",
        "usr' UNION SELECT null, null, null--",
    ]

    for attack_user in sqli_payloads:
        resp = client.post(
            f"{settings.API_V1_STR}/transactions/evaluate",
            json={
                "user_id": attack_user,
                "amount": 150.0,
                "recipient_vpa": "vendor@upi",
                "merchant_category": "grocery",
                "channel": "UPI_APP",
            },
        )
        assert resp.status_code in [400, 422], f"Expected rejection for SQLi payload '{attack_user}', got {resp.status_code}"
        assert "injection" in resp.text.lower() or "validation" in resp.text.lower()


def test_xss_script_injection_defense():
    """Verify that Cross-Site Scripting (XSS) HTML/script tags are rejected."""
    xss_payloads = [
        "<script>alert(1)</script>",
        "javascript:eval('malicious')",
        "user<iframe src='http://evil.com'>",
    ]

    for attack_user in xss_payloads:
        resp = client.post(
            f"{settings.API_V1_STR}/transactions/evaluate",
            json={
                "user_id": attack_user,
                "amount": 150.0,
                "recipient_vpa": "vendor@upi",
                "merchant_category": "grocery",
                "channel": "UPI_APP",
            },
        )
        assert resp.status_code in [400, 422]
        assert "malicious" in resp.text.lower() or "validation" in resp.text.lower() or "script" in resp.text.lower()


def test_malformed_vpa_format_enforcement():
    """Verify that malformed or syntactically invalid VPAs are rejected."""
    bad_vpas = [
        "no_at_symbol",
        "too@@many@ats",
        "store@with space@upi",
        "victim@upi; DROP TABLE transactions;--",
    ]

    for bad_vpa in bad_vpas:
        resp = client.post(
            f"{settings.API_V1_STR}/transactions/evaluate",
            json={
                "user_id": "legit_user_1",
                "amount": 150.0,
                "recipient_vpa": bad_vpa,
                "merchant_category": "grocery",
                "channel": "UPI_APP",
            },
        )
        assert resp.status_code in [400, 422]


def test_hmac_sha256_gateway_verification_flow():
    """Verify cryptographic HMAC-SHA256 signature and anti-replay verification."""
    payload = {"test": "gateway_transaction", "amount": 250.0}
    body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    now_ts = int(time.time())

    # 1. Valid Signature & Current Timestamp -> 200 OK
    valid_sig = generate_gateway_signature(body=body_bytes, timestamp=now_ts)
    resp = client.post(
        f"{settings.API_V1_STR}/system/security/verify-signature",
        content=body_bytes,
        headers={
            "X-Signature": valid_sig,
            "X-Timestamp": str(now_ts),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "authenticated"

    # 2. Tampered Body -> 403 Forbidden
    tampered_bytes = json.dumps({"test": "gateway_transaction", "amount": 9999.0}, separators=(",", ":")).encode("utf-8")
    resp_tampered = client.post(
        f"{settings.API_V1_STR}/system/security/verify-signature",
        content=tampered_bytes,
        headers={
            "X-Signature": valid_sig,
            "X-Timestamp": str(now_ts),
            "Content-Type": "application/json",
        },
    )
    assert resp_tampered.status_code == 403
    assert "signature verification failed" in resp_tampered.json()["detail"].lower()

    # 3. Replay Attack: Expired Timestamp (>300s old) -> 403 Forbidden
    expired_ts = now_ts - 500
    expired_sig = generate_gateway_signature(body=body_bytes, timestamp=expired_ts)
    resp_replay = client.post(
        f"{settings.API_V1_STR}/system/security/verify-signature",
        content=body_bytes,
        headers={
            "X-Signature": expired_sig,
            "X-Timestamp": str(expired_ts),
            "Content-Type": "application/json",
        },
    )
    assert resp_replay.status_code == 403
    assert "replay" in resp_replay.json()["detail"].lower()

    # 4. Missing Security Headers -> 401 Unauthorized
    resp_missing = client.post(
        f"{settings.API_V1_STR}/system/security/verify-signature",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert resp_missing.status_code == 401


def test_security_status_endpoint():
    """Verify GET /api/v1/system/security/status reports active posture."""
    resp = client.get(f"{settings.API_V1_STR}/system/security/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "active"
    assert data["rate_limiting"]["algorithm"] == "Token Bucket"
    assert data["gateway_authentication"]["algorithm"] == "HMAC-SHA256"
    assert data["privacy_compliance"]["regulation"] == "Digital Personal Data Protection (DPDP) Act, 2023"
