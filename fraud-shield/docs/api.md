# Fraud Shield — API Specification Snapshot

All endpoints are versioned under `/api/v1`.

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/health` | System health & active threshold configuration | None |
| `POST` | `/api/v1/transactions/evaluate` | Ingests micro-transaction and calculates risk score | API Key / HMAC |
| `GET` | `/api/v1/transactions` | Lists recently evaluated transactions | Bearer JWT |
| `GET` | `/api/v1/transactions/{txn_id}` | Retrieves detail and audit trail for a specific transaction | Bearer JWT |
| `POST` | `/api/v1/auth/verify-otp` | Validates submitted 6-digit OTP code | None |
| `POST` | `/api/v1/auth/resend-otp` | Resends OTP token (maximum 2 resends per session) | None |
| `GET` | `/api/v1/dashboard/metrics` | Streams live throughput, anomaly count, and p95 latency | Bearer JWT |

