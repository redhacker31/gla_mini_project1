"""Unit and Integration Tests for Phase 9 Real-Time Transaction Generator & Simulation."""
import time
import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.schemas.simulation import ScenarioType
from app.services.simulation_service import simulation_service
from app.services.transaction_service import transaction_service


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_simulation_env():
    """Ensure simulation generator is stopped and storage is clean."""
    init_db()
    simulation_service.stop()
    simulation_service.reset_metrics()
    transaction_service.clear_records()
    yield
    simulation_service.stop()
    simulation_service.reset_metrics()
    transaction_service.clear_records()


def test_simulation_service_start_stop_lifecycle():
    """Verify background generator start, status reporting, and clean shutdown."""
    status_initial = simulation_service.get_status()
    assert status_initial.running is False
    assert status_initial.total_generated == 0

    # Start generator at 5 TPS
    started = simulation_service.start(rate_tps=5.0, fraud_ratio=0.10, burst_interval_seconds=10)
    assert started is True
    assert simulation_service.is_running is True

    # Double start returns False
    assert simulation_service.start() is False

    status_running = simulation_service.get_status()
    assert status_running.running is True
    assert status_running.rate_tps == 5.0
    assert status_running.started_at is not None

    # Stop generator
    stopped = simulation_service.stop()
    assert stopped is True
    assert simulation_service.is_running is False


def test_trigger_routine_scenario():
    """Verify routine commerce generation yields Low Risk and Auto-Approval."""
    resp = simulation_service.trigger_scenario(
        scenario=ScenarioType.ROUTINE,
        user_id="usr_farmer_ramesh_test",
        count=3,
    )
    assert resp.scenario == "ROUTINE"
    assert resp.transactions_generated == 3
    assert len(resp.results) == 3

    for txn in resp.results:
        assert txn.status == "APPROVED"
        assert txn.risk_tier == "LOW"
        assert txn.challenge_required is False
        assert txn.composite_score < 0.45


def test_trigger_velocity_burst_attack_scenario():
    """Verify rapid-fire velocity burst triggers Step-Up OTP challenge."""
    resp = simulation_service.trigger_scenario(
        scenario=ScenarioType.VELOCITY_BURST,
        user_id="usr_automated_bot_attacker",
        count=6,
    )
    assert resp.scenario == "VELOCITY_BURST"
    assert resp.transactions_generated == 6

    # Later transactions in the burst must trigger rapid fire or elevated velocity
    burst_results = resp.results
    triggered_any_medium = any(r.risk_tier in ["MEDIUM", "HIGH"] for r in burst_results)
    assert triggered_any_medium is True

    # Check for presence of challenge session ID on challenged transactions
    challenged = [r for r in burst_results if r.status == "PENDING_VERIFICATION"]
    assert len(challenged) > 0
    assert challenged[0].session_id is not None
    assert challenged[0].session_id.startswith("otp_sess_")


def test_trigger_smurfing_attack_scenario():
    """Verify multi-mule dispersion attack elevates Shannon entropy and triggers smurfing rule."""
    resp = simulation_service.trigger_scenario(
        scenario=ScenarioType.SMURFING,
        user_id="usr_smurf_syndicate_account",
        count=6,
    )
    assert resp.scenario == "SMURFING"
    assert resp.transactions_generated >= 5

    # Check that high recipient dispersion rule fires
    all_rules = [
        rule.rule_id
        for res in resp.results
        for rule in res.triggered_rules
    ]
    assert ("RULE_RECIPIENT_CHURN" in all_rules or "RULE_RAPID_FIRE" in all_rules)


def test_trigger_blacklist_hit_scenario():
    """Verify payment to blacklisted VPA triggers High Risk Auto-Freeze."""
    resp = simulation_service.trigger_scenario(
        scenario=ScenarioType.BLACKLIST_HIT,
        user_id="usr_compromised_victim",
    )
    assert resp.scenario == "BLACKLIST_HIT"
    assert resp.transactions_generated == 1

    txn = resp.results[0]
    assert txn.risk_tier == "HIGH"
    assert txn.status == "SECURITY_FLAGGED"
    assert txn.challenge_required is False
    assert txn.composite_score >= 0.80

    rule_ids = [r.rule_id for r in txn.triggered_rules]
    assert "RULE_BLACKLISTED_RECIPIENT" in rule_ids


def test_trigger_amount_spike_scenario():
    """Verify uncharacteristic value surge triggers amount spike penalty."""
    resp = simulation_service.trigger_scenario(
        scenario=ScenarioType.AMOUNT_SPIKE,
        user_id="usr_small_merchant_target",
    )
    assert resp.scenario == "AMOUNT_SPIKE"
    # Result should reflect the sudden spike transaction
    spike_txn = resp.results[-1]
    assert spike_txn.amount >= 500.0
    rule_ids = [r.rule_id for r in spike_txn.triggered_rules]
    assert "RULE_AMOUNT_SPIKE" in rule_ids


def test_simulation_api_endpoints(client: TestClient):
    """Verify REST API: /simulation/start, /simulation/status, /simulation/trigger-scenario, /simulation/stop."""
    # 1. Check initial status
    r_stat = client.get("/api/v1/simulation/status")
    assert r_stat.status_code == 200
    assert r_stat.json()["running"] is False

    # 2. Trigger on-demand scenario via API
    r_trig = client.post("/api/v1/simulation/trigger-scenario", json={
        "scenario": "ROUTINE",
        "count": 2,
    })
    assert r_trig.status_code == 200
    d_trig = r_trig.json()
    assert d_trig["scenario"] == "ROUTINE"
    assert d_trig["transactions_generated"] == 2

    # 3. Start background simulation via API
    r_start = client.post("/api/v1/simulation/start", json={
        "rate_tps": 2.0,
        "fraud_ratio": 0.05,
        "burst_interval_seconds": 15,
    })
    assert r_start.status_code == 200
    assert r_start.json()["running"] is True

    # 4. Stop simulation via API
    r_stop = client.post("/api/v1/simulation/stop")
    assert r_stop.status_code == 200
    assert r_stop.json()["running"] is False
