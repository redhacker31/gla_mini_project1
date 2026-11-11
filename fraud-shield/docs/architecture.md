# Fraud Shield — System Architecture

## Overview
Fraud Shield is an edge-compatible, real-time behavioral anomaly detection and adaptive risk-based authentication system engineered for digital micro-transactions (< INR 1,000).

```
[ Client / Mobile Wallet Simulator ]
              │ (POST /evaluate)
              ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Ingestion & Validation Gateway (<15ms)              │
│ - Schema Validation via Pydantic                            │
│ - HMAC Signature Verification & Token Bucket Rate Limiting  │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Behavioral Velocity Feature Pipeline (<10ms)                │
│ - Sliding window transaction counts & sums (5m, 1h, 24h)     │
│ - Inter-arrival delta-t, recipient entropy, amount ratios   │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Machine Learning & Security Rule Engine (<15ms)             │
│ - Unsupervised Isolation Forest Anomaly Scoring             │
│ - Deterministic Security Rules                              │
│ - Calibrated Sigmoid Composite Risk Score S(x) in [0.0, 1.0]│
└─────────────────────────────┬───────────────────────────────┘
                              ▼
        ┌─────────────────────┼─────────────────────┐
        │ S(x) < 0.45         │ 0.45 <= S(x) < 0.80 │ S(x) >= 0.80
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────────┐    ┌─────────────────┐
│   LOW RISK   │     │   MEDIUM RISK    │    │    HIGH RISK    │
│  Auto-Allow  │     │ Step-Up SMS OTP  │    │ Freeze & Review │
└──────────────┘     └──────────────────┘    └─────────────────┘
```

## Core Components
1. **API Gateway (FastAPI)**: Asynchronous REST endpoints managing requests within sub-50ms p95 latency.
2. **Feature Pipeline**: Rolling window aggregations without future information leakage.
3. **Anomaly Engine**: Scikit-learn Isolation Forest trained on transaction behavior.
4. **Step-Up OTP Service**: CSPRNG 6-digit tokens with 180s TTL and 3-attempt brute-force protection.
5. **Persistence**: SQLite (local) / PostgreSQL (production) with salted SHA-256 pseudonymization.

