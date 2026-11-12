"""Batch Feature Pipeline for Offline ML Training and Dataset Preprocessing.

Transforms raw historical transaction records into ML-ready behavioral feature vectors.
Strictly ensures zero future data leakage by evaluating rolling windows
only over preceding transactions (t < t_current).
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import math
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

FEATURE_NAMES = [
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


def calculate_shannon_entropy(recipients: List[str]) -> float:
    """Calculate Shannon Entropy H(X) = -sum(p * log2(p)) for recipient distribution."""
    if not recipients:
        return 0.0
    n = len(recipients)
    counts: Dict[str, int] = {}
    for r in recipients:
        counts[r] = counts.get(r, 0) + 1
    entropy = 0.0
    for count in counts.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)
    return round(float(entropy), 4)


class BatchFeaturePipeline(BaseEstimator, TransformerMixin):
    """Generates rolling behavioral velocity features from a chronological transaction stream."""

    def __init__(self):
        self.feature_names = FEATURE_NAMES

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw transaction dataframe into behavioral feature matrix.
        
        Expects columns: ['user_id', 'amount', 'timestamp', 'recipient_vpa']
        """
        # Ensure proper datetime parsing and chronological ordering
        data = df.copy()
        data["_dt"] = pd.to_datetime(data["timestamp"], utc=True)
        data = data.sort_values(by=["_dt"]).reset_index(drop=True)

        features: List[Dict[str, float]] = []

        # Group by user to maintain per-account history without cross-user leakage
        # Using a chronological timeline per user
        user_histories: Dict[str, List[Tuple[float, float, str]]] = {}  # user -> [(timestamp_unix, amount, recipient)]

        for _, row in data.iterrows():
            u = str(row["user_id"])
            amt = float(row["amount"])
            dt = row["_dt"]
            t_curr = dt.timestamp()
            recipient = str(row.get("recipient_vpa", "unknown"))

            if u not in user_histories:
                user_histories[u] = []

            history = user_histories[u]

            # 1. Delta-T (Seconds since previous transaction)
            if history:
                prev_t = history[-1][0]
                delta_t = max(t_curr - prev_t, 0.0)
            else:
                delta_t = 86400.0  # Cold start: default to 24 hours (low velocity)

            # 2. Rolling window aggregations: 5m (300s), 1h (3600s), 24h (86400s)
            t_5m = t_curr - 300.0
            t_1h = t_curr - 3600.0
            t_24h = t_curr - 86400.0

            count_5m = 0
            count_1h = 0
            count_24h = 0
            sum_5m = 0.0
            sum_1h = 0.0
            recipients_1h = []
            all_historical_amounts = []

            for h_t, h_amt, h_rec in history:
                all_historical_amounts.append(h_amt)
                if h_t >= t_24h:
                    count_24h += 1
                    if h_t >= t_1h:
                        count_1h += 1
                        sum_1h += h_amt
                        recipients_1h.append(h_rec)
                        if h_t >= t_5m:
                            count_5m += 1
                            sum_5m += h_amt

            # 3. Recipient Entropy (1 hour window)
            entropy_1h = calculate_shannon_entropy(recipients_1h)

            # 4. Amount deviation ratio (amount / historical user mean)
            if all_historical_amounts:
                hist_mean = sum(all_historical_amounts) / len(all_historical_amounts)
                amt_ratio = amt / max(hist_mean, 10.0)
            else:
                amt_ratio = 1.0  # Cold start neutral baseline

            features.append({
                "amount": amt,
                "txn_count_5m": float(count_5m),
                "txn_count_1h": float(count_1h),
                "txn_count_24h": float(count_24h),
                "amount_sum_5m": float(sum_5m),
                "amount_sum_1h": float(sum_1h),
                "delta_t_seconds": float(delta_t),
                "recipient_entropy_1h": float(entropy_1h),
                "amount_deviation_ratio": round(float(amt_ratio), 4),
            })

            # Append current transaction to user history for subsequent records
            history.append((t_curr, amt, recipient))

        feature_df = pd.DataFrame(features, columns=FEATURE_NAMES)
        return feature_df
