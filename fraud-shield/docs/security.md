# Fraud Shield — Security Architecture, Hardening & STRIDE Threat Model

**Project:** Fraud Shield — Real-Time Anomaly Detection for Digital Micro-Transactions  
**Compliance Standards:** Reserve Bank of India (RBI) Master Directions on Digital Payment Security Controls (2021) & Digital Personal Data Protection (DPDP) Act, 2023  
**Implementation Phase:** Phase 13 (Security Hardening, Rate Limiting & Input Sanitization)  
**Status:** Verified & Active  

---

## 1. STRIDE Threat Model Matrix

| Threat Category | Specific Attack Vector | Potential Impact | Mitigation Architecture in Fraud Shield | Verification Evidence |
|---|---|---|---|---|
| **S — Spoofing Identity** | Attacker impersonates legitimate user or sends forged banking switch API requests. | Unauthorized funds siphon, fraudulent micro-transaction injection. | 1. **HMAC-SHA256 Gateway Signature:** Requests from partner gateways must include `X-Signature` and `X-Timestamp`. Validated in constant time.<br>2. **CSPRNG Step-Up OTP:** 6-digit cryptographic challenge tokens generated via Python `secrets`. | Tested in `test_hmac_sha256_gateway_verification_flow` and `test_otp_service.py`. |
| **T — Tampering with Data** | Attacker intercepts and modifies transaction amount, recipient VPA, or audit history. | Fund misdirection, undetected fraudulent balance extraction. | 1. **Append-Only Cryptographic Audit Ledger:** Sequential SHA-256 Merkle-style hash chaining ($H_i = \text{SHA256}(H_{i-1} \parallel \dots)$).<br>2. **HMAC Message Digest:** Re-calculated at server; body tampering invalidates signature. | Verified via `GET /api/v1/transactions/audit/verify` and `test_persistence.py`. |
| **R — Repudiation** | Transacting user or merchant denies initiating or receiving transfer. | Financial disputes, regulatory non-compliance, chargebacks. | 1. **Cryptographic Non-Repudiation:** Append-only immutable audit log recording UTC timestamps, hashed actor IDs, operational action, and prev_hash linkage.<br>2. **OTP Proof of Verification:** Challenge success states recorded in persistent session tables. | Audit log inspection at `/api/v1/transactions/audit/logs`. |
| **I — Information Disclosure** | Internal database leak or memory dump exposes customer identity or mobile numbers. | Violation of DPDP Act 2023, identity theft, customer privacy breach. | 1. **Zero Cleartext PII Storage:** Raw mobile numbers and account IDs are never persisted.<br>2. **Salted SHA-256 Pseudonymization:** All user identifiers hashed with secret system key derivation salt.<br>3. **Masked UI Displays:** Customer identifiers rendered as `usr_***9921` and VPAs as `s***e@paytm`. | Verified via `test_persistence.py` and DPDP audit tests. |
| **D — Denial of Service (DoS)** | Attacker floods API gateway with thousands of rapid requests, exhausting CPU or SQLite locks. | Legitimate micro-commerce transactions delayed beyond sub-50ms SLA budget. | 1. **Token Bucket Rate Limiting:** In-memory token bucket enforcing 120 req/min with 40-token burst capacity per client IP.<br>2. **HTTP 429 Throttling:** Dispatches standard `Retry-After` headers on violation.<br>3. **Sub-50ms CPU Execution:** Low algorithmic complexity guarantees resistance to algorithmic DoS. | Verified in `test_token_bucket_rate_limiter_throttling`. |
| **E — Elevation of Privilege** | Attacker injects malicious SQL statements or scripts into unvalidated transaction inputs. | Remote database alteration, data exfiltration, XSS injection in dashboard. | 1. **Input Sanitization & Regex Guards:** String inputs sanitized against SQLi (`UNION SELECT`, `' OR '1'='1`), XSS (`<script>`, `javascript:`), and directory traversal.<br>2. **Strict UPI VPA Syntax:** Enforces canonical `^[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,32}$`.<br>3. **OWASP HTTP Security Headers:** Enforces `nosniff`, `DENY`, and CSP. | Verified in `test_sql_injection_defense` and `test_xss_script_injection_defense`. |

---

## 2. Digital Personal Data Protection (DPDP) Act, 2023 Compliance Protocol

| DPDP Principle | Statutory Mandate | Fraud Shield Technical Implementation |
|---|---|---|
| **Principle of Purpose Limitation** | Personal data processed solely for fraud risk assessment. | No raw demographic data, GPS coordinates, or contacts requested or processed. |
| **Principle of Data Minimization** | Collect only strictly necessary micro-transaction features. | System processes only 9 behavioral velocity features ($\Delta t$, rolling counts, entropy, deviation). |
| **Storage Limitation & Zero Cleartext PII** | Sensitive personal data must not be stored in unencrypted form. | Zero storage of raw mobile phone numbers. All user IDs transformed into salted SHA-256 digests (`hash_identifier()`). |
| **Data Integrity & Traceability** | Security logs must be tamper-resistant and auditable. | Immutable append-only audit ledger with cryptographic SHA-256 sequential block hashes. |

---

## 3. Defense-in-Depth Layer Architecture

```
[ Client Request / Mobile UPI Wallet ]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 1. HTTP Security Headers Middleware                     │
│    - X-Content-Type-Options: nosniff                   │
│    - X-Frame-Options: DENY                             │
│    - Strict-Transport-Security: max-age=31536000       │
│    - Content-Security-Policy: default-src 'self' ...   │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│ 2. Token Bucket Rate Limiting Middleware               │
│    - 120 requests/minute per client IP                 │
│    - 40-token burst capacity                           │
│    - HTTP 429 Too Many Requests + Retry-After headers  │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│ 3. HMAC-SHA256 Gateway Signature & Anti-Replay Auth    │
│    - X-Signature: HMAC-SHA256(key, timestamp + . + body)│
│    - X-Timestamp: Max 300-second drift window          │
│    - Constant-time verification (hmac.compare_digest)  │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│ 4. Input Sanitization & Attack Injection Defense       │
│    - SQLi pattern detection (UNION, OR 1=1, DROP)      │
│    - XSS detection (<script>, javascript:, iframe)     │
│    - Canonical UPI VPA regex format validation         │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│ 5. Real-Time Composite Risk & Anomaly Scoring Engine   │
│    - Isolation Forest behavioral anomaly inference     │
│    - 8 Deterministic domain security rules             │
│    - Logistic sigmoid calibrated fusion S(x)           │
└────────────────────────────────────────────────────────┘
```

---

## 4. Cryptographic Specifications

- **Hash Function:** SHA-256 (FIPS 180-4 compliant).
- **HMAC Construction:** HMAC-SHA256 (RFC 2104).
- **OTP Generation:** Python `secrets.randbelow()` (CSPRNG backed by `/dev/urandom` / Windows CryptGenRandom).
- **OTP Digest Storage:** Salted SHA-256 digest with 180-second TTL; plaintext OTP wiped immediately from memory.
- **Verification Logic:** `hmac.compare_digest()` constant-time comparison to prevent timing side-channel attacks.
