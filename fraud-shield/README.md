# Fraud Shield: Real-Time Anomaly Detection for Digital Micro-Transactions

> **B.Tech AIML Capstone Project**  
> Team: Quantumm Coders (Team ID: 40) | GLA University

---

## 1. Project Overview
Vulnerable digital wallet users in rural India face increasing low-value transaction fraud (such as velocity bursts, collect-request phishing, smurfing, and micro-draining). Traditional static thresholds fail to detect these attacks because individual amounts fall beneath conventional alarm limits (< INR 500).

**Fraud Shield** is an edge-compatible, real-time AI/ML behavioral anomaly detection and adaptive risk-based authentication system that:
- Inspects streaming micro-transactions within a **sub-50ms inference budget**.
- Isolates anomalous velocity patterns using unsupervised learning (**Isolation Forest**).
- Blends ML scores with deterministic rules into a **calibrated Composite Risk Score $S(x) \in [0.0, 1.0]$**.
- Dynamically challenges suspicious transactions with **Step-Up Multi-Factor Authentication (SMS OTP verification)**.

---

## 2. Risk Decision Engine
- **Low Risk ($S(x) < 0.45$):** Legitimate routine commerce approved instantly with 0% friction.
- **Medium Risk ($0.45 \le S(x) < 0.80$):** Challenged via 6-digit CSPRNG SMS OTP (180s TTL, max 3 attempts).
- **High Risk ($S(x) \ge 0.80$):** Temporarily frozen with an automated security alert dispatched.

---

## 3. Project Structure
```
fraud-shield/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── database/
│   │   └── security/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
├── ml/
│   ├── notebooks/
│   ├── data_processing/
│   ├── training/
│   ├── evaluation/
│   └── artifacts/
├── docs/
└── README.md
```

---

## 4. Quick Start

### Backend Setup
```bash
cd fraud-shield/backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
- API Health Check: `http://127.0.0.1:8000/api/v1/health`
- Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

### Frontend Setup
```bash
cd fraud-shield/frontend
npm install
npm run dev
```
- Web Application: `http://localhost:5173`

