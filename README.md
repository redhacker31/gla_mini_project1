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

### Phase 1 Status
- [x] Project Scaffolding & Directory Structure
- [x] Backend FastAPI Ingestion Gateway & Health Check Endpoint (`/api/v1/health`)
- [x] Frontend React Vite Scaffolding with Responsive UI
- [x] Configurable Risk Thresholds (`0.45` Low, `0.80` High)
- [x] Full Pytest & Build Verification
