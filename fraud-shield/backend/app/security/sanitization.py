"""Input Sanitization, Injection Detection, and Format Enforcement.

Protects against SQL Injection, Cross-Site Scripting (XSS), Path Traversal,
Null Byte Poisoning, and malformed UPI Virtual Payment Addresses (VPAs).
"""
import math
import re
from typing import Optional


# Malicious pattern detectors
SQLI_REGEX = re.compile(
    r"(\b(UNION(\s+ALL)?|SELECT|DROP|INSERT|DELETE|UPDATE|ALTER|EXEC|XP_)\b|--|/\*|\*/|;\s*--|'\s*OR\s*'\d+'\s*=\s*'\d+|'\s*OR\s*1\s*=\s*1)",
    re.IGNORECASE,
)

XSS_REGEX = re.compile(
    r"(<script|javascript:|onerror\s*=|onload\s*=|onclick\s*=|document\.cookie|<iframe|<embed|<object|eval\s*\()",
    re.IGNORECASE,
)

PATH_TRAVERSAL_REGEX = re.compile(
    r"(\.\./|\.\.\\|/etc/passwd|c:\\windows)",
    re.IGNORECASE,
)

# Canonical UPI VPA format: [username/store]@[bank/provider]
# e.g., kirana_store.01@paytm, user-99@okhdfcbank
UPI_VPA_REGEX = re.compile(
    r"^[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,32}$"
)


def sanitize_text(
    value: str,
    field_name: str = "Input",
    max_length: int = 128,
    allow_empty: bool = False,
) -> str:
    """Sanitize and validate string inputs against injection attack vectors."""
    if value is None:
        if allow_empty:
            return ""
        raise ValueError(f"{field_name} cannot be null or None.")

    clean = value.strip()
    if not clean and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty or whitespace only.")

    # 1. Null byte check
    if "\x00" in clean:
        raise ValueError(f"{field_name} contains prohibited null byte characters.")

    # 2. Length check
    if len(clean) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length limit ({max_length} characters).")

    # 3. SQL Injection check
    if SQLI_REGEX.search(clean):
        raise ValueError(f"{field_name} contains potentially malicious SQL injection patterns.")

    # 4. XSS Script injection check
    if XSS_REGEX.search(clean):
        raise ValueError(f"{field_name} contains potentially malicious script or HTML injection markup.")

    # 5. Path traversal check
    if PATH_TRAVERSAL_REGEX.search(clean):
        raise ValueError(f"{field_name} contains prohibited directory traversal sequences.")

    return clean


def validate_vpa(vpa: str) -> str:
    """Validate and normalize a UPI Virtual Payment Address handle."""
    clean = sanitize_text(vpa, field_name="Recipient VPA", max_length=100).lower()

    # Reject dangerous punctuation
    for bad_char in [";", "'", '"', "<", ">", "\n", "\r", " "]:
        if bad_char in clean:
            raise ValueError(f"Recipient VPA contains prohibited character '{bad_char}'.")

    if not UPI_VPA_REGEX.match(clean):
        raise ValueError(
            f"Invalid UPI VPA handle '{vpa}'. Must adhere to format '<handle>@<provider>' "
            f"(e.g., store_01@upi or vendor@okhdfcbank)."
        )

    return clean


def validate_amount(amount: float) -> float:
    """Validate numeric transaction amount for micro-payments."""
    if amount is None or math.isnan(amount) or math.isinf(amount):
        raise ValueError("Transaction amount must be a finite numeric value.")

    if amount <= 0.0:
        raise ValueError("Transaction amount must be strictly greater than 0.00 INR.")

    if amount > 100000.0:
        raise ValueError("Transaction amount exceeds RBI single UPI transaction limit (INR 100,000.00).")

    return round(float(amount), 2)
