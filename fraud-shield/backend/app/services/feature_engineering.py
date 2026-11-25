"""Real-Time Sliding-Window Feature Engineering Service.

Optimized for ultra-low latency (<10ms) inference in the FastAPI gateway.
Maintains bounded in-memory sliding-window state for active transacting accounts.
"""
from collections import deque
from datetime import datetime, timedelta, timezone
import logging
import math
import threading
import time
from typing import Deque, Dict, List, Optional, Set, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class SlidingWindowBuffer:
    """Bounded chronological state buffer for a single user's micro-transactions."""

    def __init__(self, max_retention_seconds: float = 86400.0):
        # Stores tuples: (timestamp_unix: float, amount: float, recipient_vpa: str)
        self.events: Deque[Tuple[float, float, str]] = deque()
        self.max_retention = max_retention_seconds
        self.cumulative_amount: float = 0.0
        self.cumulative_count: int = 0
        self.known_devices: Set[str] = set()

    def purge_expired(self, current_time: float):
        """Remove events older than max retention (24 hours)."""
        cutoff = current_time - self.max_retention
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def get_features(self, current_time: float, current_amount: float, current_recipient: str) -> Dict[str, float]:
        """Compute backward-looking behavioral features without mutating state."""
        self.purge_expired(current_time)

        # 1. Delta-T (Time elapsed since immediately preceding transaction)
        if self.events:
            prev_time = self.events[-1][0]
            delta_t = max(current_time - prev_time, 0.0)
        else:
            delta_t = 86400.0  # Cold-start default: 24h (indicates low velocity)

        # 2. Sliding window aggregations: 5m (300s), 1h (3600s), 24h (86400s)
        t_5m = current_time - 300.0
        t_1h = current_time - 3600.0
        t_24h = current_time - 86400.0

        count_5m = 0
        count_1h = 0
        count_24h = 0
        sum_5m = 0.0
        sum_1h = 0.0
        recipients_1h: Dict[str, int] = {}

        # Scan historical events (most recent are at the end)
        for t_evt, amt_evt, rec_evt in reversed(self.events):
            if t_evt < t_24h:
                break
            count_24h += 1

            if t_evt >= t_1h:
                count_1h += 1
                sum_1h += amt_evt
                recipients_1h[rec_evt] = recipients_1h.get(rec_evt, 0) + 1

                if t_evt >= t_5m:
                    count_5m += 1
                    sum_5m += amt_evt

        # 3. Shannon Entropy of recipients in 1h window: H(R) = -sum(p * log2(p))
        entropy_1h = 0.0
        if count_1h > 0:
            for rec_count in recipients_1h.values():
                p = rec_count / count_1h
                if p > 0:
                    entropy_1h -= p * math.log2(p)

        # 4. Amount deviation ratio: amount / historical user average
        if self.cumulative_count > 0:
            user_avg = self.cumulative_amount / self.cumulative_count
            amount_ratio = current_amount / max(user_avg, 10.0)
        else:
            amount_ratio = 1.0  # Cold start neutral baseline

        return {
            "amount": float(current_amount),
            "txn_count_5m": float(count_5m),
            "txn_count_1h": float(count_1h),
            "txn_count_24h": float(count_24h),
            "amount_sum_5m": float(round(sum_5m, 2)),
            "amount_sum_1h": float(round(sum_1h, 2)),
            "delta_t_seconds": float(round(delta_t, 2)),
            "recipient_entropy_1h": float(round(entropy_1h, 4)),
            "amount_deviation_ratio": float(round(amount_ratio, 4)),
        }

    def record_transaction(
        self,
        timestamp: float,
        amount: float,
        recipient: str,
        device_hash: Optional[str] = None,
    ):
        """Append approved transaction to the state buffer."""
        self.events.append((timestamp, amount, recipient))
        self.cumulative_amount += amount
        self.cumulative_count += 1
        if device_hash:
            self.known_devices.add(device_hash)
        self.purge_expired(timestamp)


class FeatureEngineeringService:
    """Manages real-time sliding windows and computes behavioral feature vectors."""

    FEATURE_COLUMNS = [
        "amount",
        "txn_count_5m",
        "txn_count_1h",
        "txn_count_24h",
        "amount_sum_5m",
        "amount_sum_1h",
        "delta_t_seconds",
        "recipient_entropy_1h",
        "amount_deviation_ratio",
    ]

    def __init__(self):
        # In-memory dictionary: canonical user_hash (or SHA-256 key) -> SlidingWindowBuffer
        self._buffers: Dict[str, SlidingWindowBuffer] = {}
        self._device_users: Dict[str, Set[str]] = {}
        self._flagged_devices: Set[str] = set()
        self._lock = threading.RLock()

    @staticmethod
    def _is_sha256(val: str) -> bool:
        return isinstance(val, str) and len(val) == 64 and all(c in "0123456789abcdef" for c in val.lower())

    def _buffer_key(self, user_id: str) -> str:
        """Resolve raw user_id or persisted SHA-256 hash to canonical DPDP buffer key."""
        if self._is_sha256(user_id):
            return user_id.lower()
        from app.security.hashing import hash_identifier
        return hash_identifier(user_id)

    def get_or_create_buffer(self, user_id: str) -> SlidingWindowBuffer:
        key = self._buffer_key(user_id)
        with self._lock:
            # Memory safety: Periodically purge inactive user buffers if active cache exceeds threshold
            if len(self._buffers) > 10000:
                now = time.time()
                cutoff = now - 86400.0
                stale = [uid for uid, buf in self._buffers.items() if not buf.events or buf.events[-1][0] < cutoff]
                for uid in stale[:2000]:
                    del self._buffers[uid]

            if key not in self._buffers:
                self._buffers[key] = SlidingWindowBuffer()
            return self._buffers[key]

    def extract_features(
        self,
        user_id: str,
        amount: float,
        timestamp: Optional[datetime] = None,
        recipient_vpa: str = "unknown@bank",
        device_hash: Optional[str] = None,
    ) -> Dict[str, float]:
        """Extract real-time feature vector in sub-10ms latency budget.
        
        Evaluates purely preceding behavior without mutating state.
        """
        if timestamp is None:
            t_unix = time.time()
        elif isinstance(timestamp, datetime):
            t_unix = timestamp.timestamp()
        else:
            t_unix = float(timestamp)

        key = self._buffer_key(user_id)
        with self._lock:
            buffer = self.get_or_create_buffer(key)
            features = buffer.get_features(
                current_time=t_unix,
                current_amount=amount,
                current_recipient=recipient_vpa,
            )
            if device_hash:
                is_new_device = 1.0 if (len(buffer.known_devices) >= 1 and device_hash not in buffer.known_devices) else 0.0
                other_users = self._device_users.get(device_hash, set()) - {key}
                is_shared_or_flagged = 1.0 if (device_hash in self._flagged_devices or len(other_users) >= 2) else 0.0
            else:
                is_new_device = 0.0
                is_shared_or_flagged = 0.0

            features["is_new_device"] = is_new_device
            features["is_shared_or_flagged_device"] = is_shared_or_flagged
        return features

    def extract_feature_vector(
        self,
        user_id: str,
        amount: float,
        timestamp: Optional[datetime] = None,
        recipient_vpa: str = "unknown@bank",
    ) -> np.ndarray:
        """Return 1D numpy array ordered exactly according to FEATURE_COLUMNS for ML inference."""
        feats = self.extract_features(user_id, amount, timestamp, recipient_vpa)
        return np.array([feats[col] for col in self.FEATURE_COLUMNS], dtype=np.float32)

    def commit_transaction(
        self,
        user_id: str,
        amount: float,
        timestamp: Optional[datetime] = None,
        recipient_vpa: str = "unknown@bank",
        device_hash: Optional[str] = None,
        is_flagged: bool = False,
    ):
        """Record transaction into buffer once evaluated/approved."""
        if timestamp is None:
            t_unix = time.time()
        elif isinstance(timestamp, datetime):
            t_unix = timestamp.timestamp()
        else:
            t_unix = float(timestamp)

        key = self._buffer_key(user_id)
        with self._lock:
            buffer = self.get_or_create_buffer(key)
            buffer.record_transaction(t_unix, amount, recipient_vpa, device_hash=device_hash)
            if device_hash:
                if len(self._device_users) > 10000:
                    # Evict arbitrary oldest slice to cap memory
                    for k in list(self._device_users.keys())[:2000]:
                        del self._device_users[k]
                self._device_users.setdefault(device_hash, set()).add(key)
                if is_flagged:
                    self._flagged_devices.add(device_hash)

    def clear_all(self):
        """Clear all buffers and device tracking state (test isolation)."""
        with self._lock:
            self._buffers.clear()
            self._device_users.clear()
            self._flagged_devices.clear()

    def reset_user(self, user_id: str):
        """Clear user state buffer (e.g. for testing)."""
        key = self._buffer_key(user_id)
        with self._lock:
            self._buffers.pop(user_id, None)
            self._buffers.pop(key, None)

    def hydrate_from_db(self, db=None, window_hours: int = 24) -> int:
        """Hydrate sliding-window buffers from persisted SQLite transactions on startup."""
        from sqlalchemy import select
        from app.database.session import get_db_context
        from app.models.transaction import Transaction

        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        def _load(session) -> int:
            stmt = (
                select(Transaction)
                .where(Transaction.created_at >= cutoff)
                .order_by(Transaction.created_at.asc())
            )
            hydrated = 0
            result = session.scalars(stmt.execution_options(yield_per=500))
            try:
                for txn in result:
                    ts_dt = txn.created_at
                    if ts_dt is None:
                        continue
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.replace(tzinfo=timezone.utc)
                    t_unix = ts_dt.timestamp()
                    buf = self.get_or_create_buffer(txn.user_hash)
                    dev_hash = getattr(txn, "device_hash", None)
                    buf.record_transaction(
                        t_unix,
                        float(txn.amount),
                        txn.recipient_vpa_masked or "unknown@upi",
                        device_hash=dev_hash,
                    )
                    if dev_hash:
                        self._device_users.setdefault(dev_hash, set()).add(txn.user_hash)
                        if txn.status in ("SECURITY_FLAGGED", "REJECTED"):
                            self._flagged_devices.add(dev_hash)
                    hydrated += 1
            finally:
                result.close()
            return hydrated

        try:
            with self._lock:
                self._buffers.clear()
                self._device_users.clear()
                self._flagged_devices.clear()
                if db is not None:
                    count = _load(db)
                else:
                    with get_db_context() as session:
                        count = _load(session)
            logger.info("Hydrated %d transactions into %d sliding-window buffers.", count, len(self._buffers))
            return count
        except Exception as exc:
            logger.warning("Sliding-window startup hydration skipped/failed: %s", exc)
            return 0


# Singleton instance for application runtime
feature_service = FeatureEngineeringService()
