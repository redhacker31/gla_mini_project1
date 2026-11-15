"""Streaming Transaction Generator and Adversarial Simulation API Endpoints.

Provides controls for:
  - Starting and stopping background live transaction streaming
  - Triggering specific on-demand adversarial attack burst scenarios
  - Monitoring live throughput and risk tier distributions
"""
from fastapi import APIRouter, HTTPException, status

from app.schemas.simulation import (
    ScenarioTriggerRequest,
    ScenarioTriggerResponse,
    SimulationStartRequest,
    SimulationStatusResponse,
)
from app.services.simulation_service import simulation_service

router = APIRouter()


@router.post(
    "/start",
    response_model=SimulationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Background Streaming Simulation",
    description=(
        "Launches an asynchronous background worker that emits synthetic digital micro-transactions "
        "at the requested TPS, periodically interspersing adversarial attack bursts."
    ),
)
async def start_simulation(payload: SimulationStartRequest = SimulationStartRequest()):
    """Start background streaming transaction generator."""
    started = simulation_service.start(
        rate_tps=payload.rate_tps,
        fraud_ratio=payload.fraud_ratio,
        burst_interval_seconds=payload.burst_interval_seconds,
    )
    if not started and simulation_service.is_running:
        # Already running - return current status
        pass

    return simulation_service.get_status()


@router.post(
    "/stop",
    response_model=SimulationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop Background Streaming Simulation",
    description="Halts the background transaction emission worker.",
)
async def stop_simulation():
    """Halt background streaming transaction generator."""
    simulation_service.stop()
    return simulation_service.get_status()


@router.get(
    "/status",
    response_model=SimulationStatusResponse,
    summary="Query Simulation Generator Telemetry",
    description="Inspect current throughput, total transactions emitted, and live risk tier breakdown.",
)
async def get_simulation_status():
    """Retrieve generator running state and live telemetry."""
    return simulation_service.get_status()


@router.post(
    "/trigger-scenario",
    response_model=ScenarioTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute On-Demand Attack Scenario",
    description=(
        "Instantly generates and evaluates an adversarial or benign scenario pattern "
        "(ROUTINE, VELOCITY_BURST, SMURFING, BLACKLIST_HIT, AMOUNT_SPIKE) and returns real-time risk decisions."
    ),
)
async def trigger_scenario(payload: ScenarioTriggerRequest):
    """Execute on-demand attack burst or routine test batch."""
    try:
        response = simulation_service.trigger_scenario(
            scenario=payload.scenario,
            user_id=payload.user_id,
            count=payload.count,
        )
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario execution failed: {str(exc)}",
        )
