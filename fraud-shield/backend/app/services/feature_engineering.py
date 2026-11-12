"""Real-Time Sliding-Window Feature Engineering Service.

Optimized for ultra-low latency (<10ms) inference in the FastAPI gateway.
Maintains bounded in-memory sliding-window state for active transacting accounts.
"""
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Tuple
import math
import time
import numpy as np


class SlidingWindowBuffer:
    """Bounded chronological state buffer for a single user's micro-transactions."""

    def __init__(self, max_retention_seconds: float = 86400.0):
        # Stores tuples: (timestamp_unix: float, amount: float, recipient_vpa: str)
        self.events: Deque[Tuple[float, float, str]] = deque()
        self.max_retention = max_retention_seconds
        self.cumulative_amount: float = 0.0
        self.cumulative_count: int = 0

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

    def record_transaction(self, timestamp: float, amount: float, recipient: str):
        """Append approved transaction to the state buffer."""
        self.events.append((timestamp, amount, recipient))
        self.cumulative_amount += amount
        self.cumulative_count += 1
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
        # In-memory dictionary: user_id -> SlidingWindowBuffer
        self._buffers: Dict[str, SlidingWindowBuffer] = {}

    def get_or_create_buffer(self, user_id: str) -> SlidingWindowBuffer:
        if user_id not in self._buffers:
            self._buffers[user_id] = SlidingWindowBuffer()
        return self._buffers[user_id]

    def extract_features(
        self,
        user_id: str,
        amount: float,
        timestamp: Optional[datetime] = None,
        recipient_vpa: str = "unknown@bank",
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

        buffer = self.get_or_create_buffer(user_id)
        features = buffer.get_features(
            current_time=t_unix,
            current_amount=amount,
            current_recipient=recipient_vpa,
        )
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
    ):
        """Record transaction into buffer once evaluated/approved."""
        if timestamp is None:
            t_unix = time.time()
        elif isinstance(timestamp, datetime):
            t_unix = timestamp.timestamp()
        else:
            t_unix = float(timestamp)

        buffer = self.get_or_create_buffer(user_id)
        buffer.record_transaction(t_unix, amount, recipient_vpa)

    def reset_user(self, user_id: str):
        """Clear user state buffer (e.g. for testing)."""
        if user_id in self._buffers:
            del self._buffers[user_id]


# Singleton instance for application runtime
feature_service = FeatureEngineeringService()
