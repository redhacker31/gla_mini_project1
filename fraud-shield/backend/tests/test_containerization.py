"""Unit tests for Phase 14 Production Containerization & Docker Orchestration."""
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


def get_project_root() -> Path:
    """Resolve project directory root."""
    test_dir = Path(__file__).resolve().parent
    # Check parent dirs for fraud-shield or docker-compose.yml
    candidates = [
        test_dir.parent,               # fraud-shield/backend
        test_dir.parent.parent,        # fraud-shield
        test_dir.parent.parent.parent, # workspace root
    ]
    for c in candidates:
        if (c / "docker-compose.yml").exists() or (c / "fraud-shield").exists():
            return c
    return test_dir.parent.parent


def test_healthcheck_probe_endpoint():
    """Verify standard orchestrator /health probe endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.APP_NAME
    assert "risk_thresholds" in data
    assert "ml_model" in data


def test_backend_dockerfile_security_and_stages():
    """Verify backend Dockerfile implements multi-stage builds and non-root execution."""
    backend_dir = Path(__file__).resolve().parent.parent
    dockerfile_path = backend_dir / "Dockerfile"
    assert dockerfile_path.exists(), "backend/Dockerfile must exist"

    content = dockerfile_path.read_text(encoding="utf-8")
    # Multi-stage verification
    assert "AS builder" in content, "Dockerfile must feature a builder stage"
    assert "AS runtime" in content, "Dockerfile must feature a minimal runtime stage"

    # Security hardening: Non-root user
    assert "groupadd" in content and "appgroup" in content
    assert "useradd" in content and "appuser" in content
    assert "USER appuser" in content, "Runtime container must drop privileges to appuser"

    # Orchestrator Healthcheck & Entrypoint
    assert "HEALTHCHECK" in content
    assert "http://localhost:8000/health" in content
    assert "uvicorn" in content
    assert "EXPOSE 8000" in content


def test_backend_dockerignore_coverage():
    """Verify backend .dockerignore excludes virtual environments, caches, and raw databases."""
    backend_dir = Path(__file__).resolve().parent.parent
    dockerignore_path = backend_dir / ".dockerignore"
    assert dockerignore_path.exists(), "backend/.dockerignore must exist"

    content = dockerignore_path.read_text(encoding="utf-8")
    assert ".venv" in content
    assert "__pycache__" in content
    assert "*.db" in content
    assert ".pytest_cache" in content


def test_frontend_dockerfile_and_nginx_proxy():
    """Verify frontend Dockerfile and Nginx reverse proxy configuration."""
    backend_dir = Path(__file__).resolve().parent.parent
    frontend_dir = backend_dir.parent / "frontend"
    dockerfile_path = frontend_dir / "Dockerfile"
    nginx_conf_path = frontend_dir / "nginx.conf"

    assert dockerfile_path.exists(), "frontend/Dockerfile must exist"
    assert nginx_conf_path.exists(), "frontend/nginx.conf must exist"

    # Dockerfile contents
    df_content = dockerfile_path.read_text(encoding="utf-8")
    assert "node:20-alpine" in df_content or "node:" in df_content
    assert "nginx:" in df_content
    assert "npm run build" in df_content
    assert "HEALTHCHECK" in df_content

    # Nginx configuration contents
    conf_content = nginx_conf_path.read_text(encoding="utf-8")
    assert "proxy_pass http://backend:8000/api/;" in conf_content, "Nginx must reverse proxy /api/ to backend"
    assert "try_files $uri $uri/ /index.html;" in conf_content, "Nginx must support SPA client routing"
    assert "gzip on;" in conf_content, "Nginx must enable gzip compression"
    assert "X-Frame-Options" in conf_content, "Nginx must inject security headers"


def test_docker_compose_orchestration_specs():
    """Verify Docker Compose configurations define healthy multi-service topologies."""
    backend_dir = Path(__file__).resolve().parent.parent
    fraud_shield_compose = backend_dir.parent / "docker-compose.yml"
    assert fraud_shield_compose.exists(), "fraud-shield/docker-compose.yml must exist"

    content = fraud_shield_compose.read_text(encoding="utf-8")
    # Services
    assert "backend:" in content
    assert "frontend:" in content

    # Volumes and Networks
    assert "fraud-shield-data:" in content or "fraud_shield_persistent_storage" in content
    assert "fraud-shield-net:" in content or "fraud_shield_network" in content

    # Inter-service dependency
    assert "condition: service_healthy" in content, "Frontend must depend on backend service_healthy condition"
