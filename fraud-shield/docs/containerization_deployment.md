# Fraud Shield - Production Containerization & Multi-Service Orchestration Guide

**Project:** Fraud Shield — Real-Time Anomaly Detection for Digital Micro-Transactions  
**Academic Context:** B.Tech CSE AIML Capstone Project, GLA University  
**Team:** Quantumm Coders (Team ID: 40)  
**Phase:** 14 — Production Containerization & Multi-Service Orchestration (Docker)

---

## 1. Architectural Overview

Fraud Shield is packaged as a cloud-native, multi-service architecture using modern containerization standards. The system orchestrates an isolated, edge-compatible deployment containing the FastAPI ASGI ingestion engine, scikit-learn Isolation Forest ML pipeline, SQLite 2.0 WAL persistence, and the React analyst telemetry dashboard served via an Nginx reverse proxy.

```
                         [ External Client / Analyst Browser ]
                                          |
                                   HTTP / :5173
                                          v
+-----------------------------------------------------------------------------------+
| fraud_shield_network (Docker Bridge Network)                                      |
|                                                                                   |
|  +-------------------------------------+   +------------------------------------+ |
|  | frontend (fraud-shield-frontend)    |   | backend (fraud-shield-backend)     | |
|  | - Nginx 1.27 Alpine                 |   | - Python 3.12 Slim                 | |
|  | - Port 80 (Published 5173:80)       |   | - Port 8000 (Published 8000:8000)  | |
|  | - Static Assets + Gzip Cache        |   | - Non-root execution (appuser)     | |
|  | - Reverse Proxy:                    |   | - Uvicorn ASGI Multi-Worker        | |
|  |     /api/*  -------- Proxy Pass --->|   | - Isolation Forest Inference       | |
|  |     /health -------- Proxy Pass --->|   | - SQLite WAL + Cryptographic Ledger| |
|  +-------------------------------------+   +-----------------+------------------+ |
|                                                              |                    |
+--------------------------------------------------------------|--------------------+
                                                               v
                                             +------------------------------------+
                                             | fraud_shield_persistent_storage    |
                                             | - /app/data/fraud_shield.db        |
                                             | - WAL journal & Cryptographic Ring |
                                             +------------------------------------+
```

---

## 2. Container Specifications & Security Hardening

### 2.1 Backend Container (`backend/Dockerfile`)
- **Base OS:** `python:3.12-slim-bookworm` (Debian 12 minimal base).
- **Multi-Stage Build:**
  - **Stage 1 (Builder):** Installs native build toolchains (`gcc`, `g++`, `libffi-dev`) to compile scientific C-extensions (NumPy, Scikit-learn), installing packages into `/root/.local`.
  - **Stage 2 (Runtime):** Discards build tools and unneeded package caches. Copies only user-installed Python binaries from builder, reducing attack surface and image size.
- **Principle of Least Privilege (Zero-Root):**
  - Creates dedicated unprivileged system group `appgroup` (GID 1000) and user `appuser` (UID 1000).
  - Drops root privileges before server startup (`USER appuser`).
- **Healthcheck Probe:**
  - Standard periodic polling (`curl -f http://localhost:8000/health`) verifying that FastAPI and SQLite connections are operational.
- **ASGI Process Model:** Runs `uvicorn` with 2 worker processes and structured access logging.

### 2.2 Frontend Container (`frontend/Dockerfile`)
- **Base OS:** `node:20-alpine` (Builder) $\rightarrow$ `nginx:1.27-alpine` (Runtime).
- **Multi-Stage Build:**
  - **Stage 1 (Builder):** Uses `npm ci` with caching layers to compile production React assets (`dist/`).
  - **Stage 2 (Runtime):** Copies static HTML/CSS/JS artifacts into `/usr/share/nginx/html` and deploys a custom `nginx.conf`.
- **Nginx Reverse Proxy & Edge Optimizations:**
  - **SPA Client Routing:** Seamless fallback `try_files $uri $uri/ /index.html;` for client-side navigation.
  - **API Gateway Routing:** Automatic reverse-proxying of `/api/` calls directly to `http://backend:8000/api/`, eliminating CORS issues in production.
  - **Gzip Compression:** Pre-compresses text, CSS, JSON, JavaScript, and SVG assets exceeding 1 KB.
  - **Immutable Caching:** Sets `Cache-Control: public, max-age=31536000, immutable` for versioned bundle chunks, while ensuring `index.html` is never cached.
  - **OWASP Header Injections:** Injects `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy`.

---

## 3. Deployment & Orchestration Guide

### 3.1 Prerequisites
- Docker Engine $\ge 24.0.0$ or Docker Desktop
- Docker Compose $\ge$ v2.20.0

### 3.2 Launching the Stack
From the project root directory, run:

```bash
# Build and start all services in detached mode
docker compose up --build -d
```

### 3.3 Verifying Service Health
Check running container states and health probes:

```bash
docker compose ps
```

*Expected output:*
```
NAME                    IMAGE                    COMMAND                  SERVICE    STATUS              PORTS
fraud-shield-backend    fraud-shield-backend     "uvicorn app.main:ap…"   backend    healthy (running)   0.0.0.0:8000->8000/tcp
fraud-shield-frontend   fraud-shield-frontend    "/docker-entrypoint.…"   frontend   healthy (running)   0.0.0.0:5173->80/tcp
```

### 3.4 Accessing the Interfaces
- **React Analyst Dashboard:** [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Service Health Probe:** [http://localhost:8000/health](http://localhost:8000/health) or [http://localhost:5173/health](http://localhost:5173/health)

### 3.5 Inspecting Live Logs
```bash
# Tail logs across all services
docker compose logs -f

# Tail backend service logs only
docker compose logs -f backend

# Tail frontend reverse proxy logs only
docker compose logs -f frontend
```

### 3.6 Stopping & Resetting the Stack
```bash
# Graceful stop
docker compose down

# Stop and purge persistent data volumes
docker compose down -v
```

---

## 4. Environment Variables Configuration Matrix

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Runtime mode (`development`, `staging`, `production`) |
| `DEBUG` | `false` | Enables/disables verbose FastAPI debugging |
| `DATABASE_URL` | `sqlite:////app/data/fraud_shield.db` | SQLite connection URL pointing to the persistent volume mount |
| `MODEL_ARTIFACT_PATH` | `/app/artifacts/isolation_forest_pipeline.joblib` | Absolute path to serialized scikit-learn model artifact |
| `RATE_LIMIT_ENABLED` | `true` | Enables/disables Token Bucket IP rate limiting |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `120` | Sustained token refill rate per client IP |
| `RATE_LIMIT_BURST_CAPACITY` | `40` | Maximum burst bucket capacity |
| `SECURITY_HEADERS_ENABLED` | `true` | Injects OWASP defense-in-depth headers |
| `RISK_THRESHOLD_LOW` | `0.45` | Frictionless auto-approval score ceiling |
| `RISK_THRESHOLD_HIGH` | `0.80` | High-risk auto-block score threshold |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:5173", ...]` | Permitted origins for Cross-Origin Resource Sharing |

---

## 5. Persistent Volume Management

The database and cryptographic audit ledgers are preserved in the named Docker volume `fraud_shield_persistent_storage`.

### Backup Database Volume
```bash
docker run --rm \
  -v fraud_shield_persistent_storage:/data \
  -v $(pwd)/backups:/backup \
  alpine tar -czvf /backup/fraud_shield_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### Restore Database Volume
```bash
docker run --rm \
  -v fraud_shield_persistent_storage:/data \
  -v $(pwd)/backups:/backup \
  alpine sh -c "cd /data && tar -xzvf /backup/<backup-filename>.tar.gz"
```
