# Fraud Shield — Security Architecture & STRIDE Threat Model

## Compliance & Standards
- **RBI Master Directions on Digital Payment Security Controls (2021)**: Risk-based Step-Up authentication for anomalous payment attempts.
- **Digital Personal Data Protection (DPDP) Act, 2023**: Data minimization and salted SHA-256 pseudonymization. Zero cleartext storage of mobile numbers or sensitive credentials.

## STRIDE Threat Mitigations
- **Spoofing / Tampering**: CSPRNG 6-digit OTP generation via Python `secrets`, 180s TTL, max 3 attempts limit, replay rejection.
- **Information Disclosure**: Salted SHA-256 for user phone numbers; HMAC request authentication.
- **Denial of Service**: Token bucket rate limiting (100 req/min) on incoming API endpoints.
- **Adversarial Evasion (Smurfing)**: Multi-scale sliding window tracking (5m, 1h, 24h) to catch micro-burst attacks beneath static rupee limits.

