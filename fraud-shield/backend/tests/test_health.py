"""Unit tests for system foundation and health check endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint responds with service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == settings.APP_NAME
    assert "health" in data


def test_health_check_endpoint():
    """Verify health check endpoint returns 200 OK and expected risk thresholds."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.APP_NAME
    assert data["risk_thresholds"]["low"] == 0.45
    assert data["risk_thresholds"]["high"] == 0.80


def test_submodule_routers_mounted():
    """Verify that all initial subrouters are mounted and responsive."""
    # Transactions router
    tx_resp = client.get(f"{settings.API_V1_STR}/transactions")
    assert tx_resp.status_code == 200

    # Auth router
    auth_resp = client.get(f"{settings.API_V1_STR}/auth/status")
    assert auth_resp.status_code == 200

    # Dashboard metrics router
    dash_resp = client.get(f"{settings.API_V1_STR}/dashboard/metrics")
    assert dash_resp.status_code == 200

