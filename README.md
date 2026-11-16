# gla_mini_project1 - Fraud Shield

## Real-Time Anomaly Detection for Digital Micro-Transactions
**B.Tech Artificial Intelligence & Machine Learning (AIML) Capstone Project**  
- **Team Name & ID:** Quantumm Coders (Team ID: 40)
- **Institution:** GLA University

---

### Project Repository Overview
This repository contains the source code, machine learning pipelines, and documentation for **Fraud Shield**, an edge-compatible, real-time behavioral anomaly detection and adaptive risk-based authentication system for digital micro-transactions.

### Directory Structure
- [`fraud-shield/`](./fraud-shield): Main project codebase.
  - [`backend/`](./fraud-shield/backend): FastAPI ASGI REST service, configuration, services, and tests.
  - [`frontend/`](./fraud-shield/frontend): React (Vite) monitoring dashboard & simulator.
  - [`ml/`](./fraud-shield/ml): Machine learning models (Isolation Forest), datasets, and notebooks.
  - [`docs/`](./fraud-shield/docs): System architecture, API specification, security threat model, and evaluation framework.
- [`Fraud_Shield_Project_Synopsis_finalpdf.pdf`](./Fraud_Shield_Project_Synopsis_finalpdf.pdf): Approved academic project synopsis.

---

### Phase Status
- [x] **Phase 1:** Project Scaffolding, Backend FastAPI Ingestion Gateway & Frontend React Vite Foundation
- [x] **Phase 2:** Dataset Acquisition, Benchmark Schemas (PaySim & ULB), UPI Synthesizer & Class Imbalance EDA
- [x] **Phase 3:** Data Cleaning, Sliding-Window Feature Engineering Pipeline & Shannon Entropy
- [x] **Phase 4:** Isolation Forest Anomaly Detection Model Training, Normalization & Latency Profiling
- [x] **Phase 5:** Composite Risk Engine (Sigmoid Fusion, Deterministic Domain Rules & 3-Tier Classification)
- [x] **Phase 6:** Transaction Evaluation API Endpoints, Pydantic v2 Contracts & Orchestration Service
- [x] **Phase 7:** SQLite & SQLAlchemy 2.0 Persistence, Pseudonymization & Append-Only Audit Ledger
- [x] **Phase 8:** Adaptive OTP Step-Up Authentication Service & Challenge Lifecycle
- [x] **Phase 9:** Real-Time Transaction Generator & Adversarial Attack Simulation Service
- [x] **Phase 10:** Interactive React Analyst Dashboard & Live Threat Telemetry
- [x] **Phase 11:** Fraud Scenario Simulator & Rule/ML Explainability Visualizations
- [x] **Phase 12:** Rigorous Performance Benchmarking & Sub-50ms Concurrency Profiling
- [x] **Phase 13:** Security Hardening, Rate Limiting & Input Sanitization
- [x] **Phase 14:** Production Containerization & Multi-Service Orchestration (Docker)
- [x] **Phase 15:** Capstone Documentation, Demonstration Script & Final Report

---

### Capstone Documentation & Deliverables
- [**Final Technical Capstone Report**](./fraud-shield/docs/final_capstone_report.md): Full academic report covering mathematical formulations, Isolation Forest scoring, sigmoid fusion, empirical evaluations, and DPDP Act 2023 compliance.
- [**Interactive Evaluator Viva & Demo Script**](./fraud-shield/docs/demo_script.md): Step-by-step 10-minute presentation and live walkthrough script covering 7 operational scenarios and viva defense Q&A.
- [**System Performance & Latency Benchmark Report**](./fraud-shield/docs/performance_benchmarks.md): Subcomponent latency breakdown (Feature Extraction: 0.08ms, ML: 10.07ms, Persistence: 8.99ms, p95: 17.27ms < 50ms) and multi-threaded stress tests.
- [**Security Hardening & STRIDE Threat Model**](./fraud-shield/docs/security.md): Threat mitigation matrix, Token Bucket rate limiting, HMAC-SHA256 signature verification, and input sanitization.
- [**Cloud-Native Containerization & Deployment Guide**](./fraud-shield/docs/containerization_deployment.md): Multi-stage Docker builds, Nginx reverse proxy, and Docker Compose orchestration.
- [**Approved Project Synopsis**](./Fraud_Shield_Project_Synopsis_finalpdf.pdf): University-approved B.Tech capstone project synopsis.

---

### Key Empirical Performance Metrics
- **PR-AUC:** **0.8119** (Target: $\ge 0.75$)
- **Recall @ 1% FPR:** **80.56%** (Target: $\ge 75.0\%$)
- **ROC-AUC:** **0.9826**
- **End-to-End Latency:** **Mean: 12.15 ms**, **p95: 17.27 ms** (SLA Budget: $\le 50.0\text{ ms}$)
- **Concurrent Throughput:** **53.7 Requests/second** (0.0% failure rate)
- **Automated Test Coverage:** **76 / 76 Unit & Integration Tests Passing** (100%)

---

### Docker Multi-Service Orchestration
Launch the containerized system (FastAPI backend + React Vite on Nginx reverse proxy + SQLite WAL persistence volume):

```bash
# Build and launch all services in detached mode
docker compose up --build -d

# Verify container health probes
docker compose ps
```
- **React Analyst Dashboard:** [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Healthcheck Probe:** [http://localhost:8000/health](http://localhost:8000/health)
