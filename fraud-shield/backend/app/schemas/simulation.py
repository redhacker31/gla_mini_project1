"""Pydantic Schemas for Streaming Transaction Generator & Adversarial Simulation."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.transaction import TransactionEvaluateResponse


class ScenarioType(str, Enum):
    """Supported simulation scenario patterns."""
    ROUTINE = "ROUTINE"
    VELOCITY_BURST = "VELOCITY_BURST"
    SMURFING = "SMURFING"
    BLACKLIST_HIT = "BLACKLIST_HIT"
    AMOUNT_SPIKE = "AMOUNT_SPIKE"


class SimulationStartRequest(BaseModel):
    """Configuration to start background transaction generator."""

    rate_tps: float = Field(
        default=2.0,
        ge=0.1,
        le=50.0,
        description="Target streaming emission rate (transactions per second)",
        examples=[2.0],
    )
    fraud_ratio: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Fraction of transactions configured as synthetic adversarial attacks",
        examples=[0.05],
    )
    burst_interval_seconds: int = Field(
        default=15,
        ge=5,
        le=300,
        description="Seconds between intermittent adversarial attack bursts",
        examples=[15],
    )


class SimulationStatusResponse(BaseModel):
    """Status report for the background streaming simulation engine."""

    running: bool
    rate_tps: float
    fraud_ratio: float
    total_generated: int
    approved_count: int
    challenged_count: int
    frozen_count: int
    avg_latency_ms: float
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0


class ScenarioTriggerRequest(BaseModel):
    """On-demand trigger for an adversarial or benign transaction sequence."""

    scenario: ScenarioType = Field(
        ...,
        description="Type of scenario: ROUTINE, VELOCITY_BURST, SMURFING, BLACKLIST_HIT, AMOUNT_SPIKE",
        examples=[ScenarioType.VELOCITY_BURST],
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional custom user account identifier",
        examples=["usr_live_scenario_01"],
    )
    count: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of transactions to execute in this sequence",
        examples=[5],
    )


class ScenarioTriggerResponse(BaseModel):
    """Evaluation outcomes resulting from an on-demand triggered scenario."""

    scenario: str
    transactions_generated: int
    results: List[TransactionEvaluateResponse]
    summary: str
