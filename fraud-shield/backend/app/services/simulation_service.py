"""Real-Time Transaction Generator & Adversarial Simulation Service.

Provides background streaming transaction generation and on-demand attack burst triggers:
  1. Routine Benign Commerce (Poisson arrival, INR 15–250, low velocity)
  2. Velocity Burst Attack (<15s inter-arrival, sub-500 amount evasion)
  3. Multi-Mule Smurfing Attack (High recipient Shannon entropy H >= 1.8)
  4. Blacklist Syndicate Attack (Known mule handles -> immediate freeze)
  5. Uncharacteristic Amount Spike (>3.5x user baseline)
"""
import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
import logging
import random
import time
from typing import Any, Deque, Dict, List, Optional
import uuid

from app.schemas.simulation import (
    ScenarioTriggerResponse,
    ScenarioType,
    SimulationStatusResponse,
)
from app.schemas.transaction import (
    TransactionEvaluateRequest,
    TransactionEvaluateResponse,
)
from app.services.transaction_service import transaction_service

logger = logging.getLogger(__name__)


# Realistic simulated user pool
BENIGN_USERS = [
    "usr_ramesh_farmer_01",
    "usr_priya_teacher_02",
    "usr_suresh_driver_03",
    "usr_anita_nurse_04",
    "usr_manoj_electrician_05",
    "usr_kavita_tailor_06",
    "usr_deepak_carpenter_07",
    "usr_sunita_student_08",
]

# Realistic benign merchant VPAs
BENIGN_MERCHANTS = [
    ("tea.stall@okaxis", "food", 15.0, 40.0),
    ("kirana.mart@paytm", "grocery", 45.0, 250.0),
    ("ration.shop@sbi", "grocery", 80.0, 350.0),
    ("dairy.booth@ybl", "grocery", 30.0, 120.0),
    ("medical.store@okicici", "healthcare", 60.0, 400.0),
    ("auto.rickshaw@upi", "transport", 20.0, 80.0),
    ("vegetable.vendor@paytm", "grocery", 25.0, 150.0),
    ("mobile.recharge@jio", "utilities", 49.0, 239.0),
]

# Attack targets
KNOWN_BLACKLIST_VPAS = [
    "attacker_mule4@ybl",
    "phishing_collect999@upi",
    "scam_qr@oksbi",
    "fraud_siphon@paytm",
    "mule_drainer@ibl",
]

SMURF_MULE_VPAS = [
    "mule_wallet_alpha@ybl",
    "mule_pay_beta@paytm",
    "mule_cash_gamma@okaxis",
    "mule_node_delta@oksbi",
    "mule_agent_epsilon@ibl",
    "mule_target_zeta@upi",
]


class SimulationService:
    """Controls background streaming generation and on-demand scenario testing."""

    def __init__(self):
        self._running: bool = False
        self._rate_tps: float = 2.0
        self._fraud_ratio: float = 0.05
        self._burst_interval_seconds: int = 15
        self._started_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None

        # Live telemetry counters
        self._total_generated: int = 0
        self._approved_count: int = 0
        self._challenged_count: int = 0
        self._frozen_count: int = 0
        self._recent_latencies: Deque[float] = deque(maxlen=200)

        # Attack cycle timing
        self._last_burst_time: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> SimulationStatusResponse:
        """Query current streaming engine status and live evaluation telemetry."""
        uptime = 0.0
        if self._running and self._started_at:
            uptime = (datetime.now(timezone.utc) - self._started_at).total_seconds()

        avg_lat = (
            sum(self._recent_latencies) / len(self._recent_latencies)
            if self._recent_latencies
            else 0.0
        )

        return SimulationStatusResponse(
            running=self._running,
            is_running=self._running,
            rate_tps=self._rate_tps,
            current_tps=self._rate_tps,
            fraud_ratio=self._fraud_ratio,
            total_generated=self._total_generated,
            approved_count=self._approved_count,
            challenged_count=self._challenged_count,
            frozen_count=self._frozen_count,
            avg_latency_ms=round(avg_lat, 2),
            started_at=self._started_at,
            uptime_seconds=round(uptime, 1),
        )

    def start(
        self,
        rate_tps: float = 2.0,
        fraud_ratio: float = 0.05,
        burst_interval_seconds: int = 15,
    ) -> bool:
        """Start background streaming transaction generator."""
        if self._running:
            return False

        self._rate_tps = max(0.1, min(rate_tps, 50.0))
        self._fraud_ratio = max(0.0, min(fraud_ratio, 1.0))
        self._burst_interval_seconds = max(5, burst_interval_seconds)
        self._started_at = datetime.now(timezone.utc)
        self._running = True
        self._last_burst_time = time.time()

        # Launch async task on the active event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._generator_loop())
        logger.info(
            "Transaction simulation engine started at %.1f TPS (fraud ratio: %.2f)",
            self._rate_tps,
            self._fraud_ratio,
        )
        return True

    def stop(self) -> bool:
        """Stop background streaming transaction generator."""
        if not self._running:
            return False

        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        logger.info("Transaction simulation engine stopped.")
        return True

    async def _generator_loop(self):
        """Infinite async background worker emitting simulated transactions."""
        try:
            while self._running:
                now = time.time()
                # Check whether to trigger an adversarial burst
                if (
                    self._fraud_ratio > 0.0
                    and (now - self._last_burst_time) >= self._burst_interval_seconds
                ):
                    self._last_burst_time = now
                    # Randomly pick an adversarial attack scenario
                    attack_type = random.choice([
                        ScenarioType.VELOCITY_BURST,
                        ScenarioType.SMURFING,
                        ScenarioType.BLACKLIST_HIT,
                    ])
                    await self._emit_scenario_async(attack_type)
                else:
                    # Emit standard benign micro-transaction
                    req = self._build_routine_request()
                    self._evaluate_and_record(req)

                # Sleep to maintain requested throughput
                sleep_sec = max(0.01, 1.0 / self._rate_tps)
                await asyncio.sleep(sleep_sec)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Simulation loop error: %s", exc, exc_info=True)
            self._running = False

    def trigger_scenario(
        self,
        scenario: ScenarioType,
        user_id: Optional[str] = None,
        count: Optional[int] = None,
    ) -> ScenarioTriggerResponse:
        """Synchronously execute an on-demand scenario and return evaluation results."""
        results: List[TransactionEvaluateResponse] = []

        if scenario == ScenarioType.ROUTINE:
            n = count or 1
            now = datetime.now(timezone.utc)
            for i in range(n):
                # If specific user_id is provided, space out timestamps by 6 hours to reflect realistic diurnal gaps
                if user_id:
                    target_user = user_id
                    sim_ts = now - timedelta(hours=6 * (n - 1 - i))
                else:
                    target_user = BENIGN_USERS[i % len(BENIGN_USERS)]
                    sim_ts = now

                req = self._build_routine_request(user_id=target_user)
                req.timestamp = sim_ts
                resp = self._evaluate_and_record(req)
                results.append(resp)
            summary = (
                f"Generated {len(results)} routine benign micro-transaction(s) for '{user_id or 'benign users'}'. "
                f"Expected verdict: LOW Risk (Auto-Approved)."
            )

        elif scenario == ScenarioType.VELOCITY_BURST:
            target_user = user_id or f"usr_bot_burst_{uuid.uuid4().hex[:6]}"
            n = count or 6
            # Emit rapid sequential payments to the same or rotating recipient
            for i in range(n):
                amount = round(random.uniform(90.0, 480.0), 2)
                req = TransactionEvaluateRequest(
                    user_id=target_user,
                    amount=amount,
                    recipient_vpa=f"smurf_node_{i % 3}@paytm",
                    merchant_category="p2p",
                    channel="UPI_APP",
                )
                resp = self._evaluate_and_record(req)
                results.append(resp)
                # Sub-second rapid firing
                time.sleep(0.02)
            summary = (
                f"Executed rapid-fire velocity burst attack ({n} transactions in <1s) for '{target_user}'. "
                f"Triggers RULE_RAPID_FIRE and RULE_VELOCITY_BURST -> Step-Up OTP Challenge."
            )

        elif scenario == ScenarioType.SMURFING:
            target_user = user_id or f"usr_smurfer_{uuid.uuid4().hex[:6]}"
            mule_targets = list(SMURF_MULE_VPAS)
            random.shuffle(mule_targets)
            n = count or len(mule_targets)
            for i in range(min(n, len(mule_targets))):
                amount = round(random.uniform(320.0, 495.0), 2)  # Sub-500 evasion
                req = TransactionEvaluateRequest(
                    user_id=target_user,
                    amount=amount,
                    recipient_vpa=mule_targets[i],
                    merchant_category="p2p",
                    channel="UPI_APP",
                )
                resp = self._evaluate_and_record(req)
                results.append(resp)
                time.sleep(0.03)
            summary = (
                f"Executed multi-mule dispersion smurfing attack ({len(results)} distinct mules) for '{target_user}'. "
                f"Elevates recipient Shannon entropy H >= 1.8 -> RULE_RECIPIENT_CHURN flagged."
            )

        elif scenario == ScenarioType.BLACKLIST_HIT:
            target_user = user_id or f"usr_victim_{uuid.uuid4().hex[:6]}"
            blacklist_vpa = random.choice(KNOWN_BLACKLIST_VPAS)
            req = TransactionEvaluateRequest(
                user_id=target_user,
                amount= round(random.uniform(200.0, 950.0), 2),
                recipient_vpa=blacklist_vpa,
                merchant_category="p2p",
                channel="COLLECT_REQUEST",
            )
            resp = self._evaluate_and_record(req)
            results.append(resp)
            summary = (
                f"Dispatched payment attempt to blacklisted destination '{blacklist_vpa}'. "
                f"Triggers RULE_BLACKLISTED_RECIPIENT (penalty +2.50) -> Auto-Freeze (High Risk)."
            )

        elif scenario == ScenarioType.AMOUNT_SPIKE:
            target_user = user_id or f"usr_spiker_{uuid.uuid4().hex[:6]}"
            # Establish baseline with 3 small payments (INR 30)
            for _ in range(3):
                base_req = TransactionEvaluateRequest(
                    user_id=target_user,
                    amount=30.0,
                    recipient_vpa="local_tea@upi",
                    merchant_category="food",
                    channel="QR_SCAN",
                )
                self._evaluate_and_record(base_req)

            # Sudden 25x uncharacteristic spike
            spike_req = TransactionEvaluateRequest(
                user_id=target_user,
                amount=850.0,
                recipient_vpa="unknown_luxury@upi",
                merchant_category="shopping",
                channel="UPI_APP",
            )
            resp = self._evaluate_and_record(spike_req)
            results.append(resp)
            summary = (
                f"Triggered uncharacteristic amount spike (INR 850 vs INR 30 baseline) for '{target_user}'. "
                f"Triggers RULE_AMOUNT_SPIKE (>3.5x baseline)."
            )
        else:
            summary = f"Unknown scenario type '{scenario}'."

        return ScenarioTriggerResponse(
            scenario=scenario.value,
            transactions_generated=len(results),
            count=len(results),
            results=results,
            evaluations=results,
            summary=summary,
        )

    async def _emit_scenario_async(self, scenario: ScenarioType):
        """Internal helper for background loop to emit attack bursts asynchronously."""
        if scenario == ScenarioType.VELOCITY_BURST:
            user = f"usr_bot_{uuid.uuid4().hex[:6]}"
            for i in range(5):
                req = TransactionEvaluateRequest(
                    user_id=user,
                    amount=round(random.uniform(150.0, 480.0), 2),
                    recipient_vpa=f"bot_cashout_{i % 2}@paytm",
                    merchant_category="p2p",
                )
                self._evaluate_and_record(req)
                await asyncio.sleep(0.05)

        elif scenario == ScenarioType.SMURFING:
            user = f"usr_smurf_{uuid.uuid4().hex[:6]}"
            for mule in SMURF_MULE_VPAS[:4]:
                req = TransactionEvaluateRequest(
                    user_id=user,
                    amount=round(random.uniform(300.0, 490.0), 2),
                    recipient_vpa=mule,
                    merchant_category="p2p",
                )
                self._evaluate_and_record(req)
                await asyncio.sleep(0.05)

        elif scenario == ScenarioType.BLACKLIST_HIT:
            user = f"usr_victim_{uuid.uuid4().hex[:6]}"
            req = TransactionEvaluateRequest(
                user_id=user,
                amount=round(random.uniform(150.0, 800.0), 2),
                recipient_vpa=random.choice(KNOWN_BLACKLIST_VPAS),
                merchant_category="p2p",
            )
            self._evaluate_and_record(req)

    def _build_routine_request(self, user_id: Optional[str] = None) -> TransactionEvaluateRequest:
        """Construct realistic benign Indian UPI micro-transaction."""
        user = user_id or random.choice(BENIGN_USERS)
        vpa, cat, min_amt, max_amt = random.choice(BENIGN_MERCHANTS)
        amount = round(random.uniform(min_amt, max_amt), 2)
        channel = random.choice(["QR_SCAN", "UPI_APP"])

        return TransactionEvaluateRequest(
            user_id=user,
            amount=amount,
            recipient_vpa=vpa,
            merchant_category=cat,
            channel=channel,
        )

    def _evaluate_and_record(self, request: TransactionEvaluateRequest) -> TransactionEvaluateResponse:
        """Evaluate transaction through TransactionService and update streaming metrics."""
        response = transaction_service.evaluate_transaction(request)

        # Update telemetry
        self._total_generated += 1
        if response.risk_tier == "LOW":
            self._approved_count += 1
        elif response.risk_tier == "MEDIUM":
            self._challenged_count += 1
        else:
            self._frozen_count += 1

        self._recent_latencies.append(response.latency_ms)
        return response

    def reset_metrics(self):
        """Reset live counters (for test isolation)."""
        self._total_generated = 0
        self._approved_count = 0
        self._challenged_count = 0
        self._frozen_count = 0
        self._recent_latencies.clear()


# Singleton instance for application runtime
simulation_service = SimulationService()
