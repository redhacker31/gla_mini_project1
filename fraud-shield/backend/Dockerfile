# ==============================================================================
# Fraud Shield Backend Dockerfile
# Production Multi-Stage, Security-Hardened Container for FastAPI Gateway
# B.Tech AIML Capstone Project - GLA University
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies for compiling scientific/C extensions if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to user site-packages
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Minimal Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

LABEL maintainer="Quantumm Coders (Team ID: 40) - GLA University"
LABEL description="Fraud Shield Real-Time Micro-Transaction Anomaly Detection Backend"
LABEL version="1.0.0"

# Install curl for container health check probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security hardening: Create unprivileged system user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    PORT=8000 \
    ENVIRONMENT=production \
    DEBUG=false \
    DATABASE_URL=sqlite:////app/data/fraud_shield.db \
    MODEL_ARTIFACT_PATH=/app/artifacts/isolation_forest_pipeline.joblib

WORKDIR /app

# Copy compiled python dependencies from builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Create persistent storage directories with unprivileged ownership
RUN mkdir -p /app/data /app/artifacts && \
    chown -R appuser:appgroup /app

# Copy application source code and artifacts
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup artifacts /app/artifacts
COPY --chown=appuser:appgroup requirements.txt pytest.ini /app/

# Switch to unprivileged runtime user
USER appuser

# Expose backend REST port
EXPOSE 8000

# Container healthcheck using orchestrator probe route
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch ASGI production server with single worker so in-memory sliding windows,
# OTP sandbox state, rate limiter, and SQLite WAL stay strongly consistent.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--access-log"]
