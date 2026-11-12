"""Unit and Performance Tests for Phase 3 Behavioral Feature Engineering."""
from datetime import datetime, timezone
import time
import numpy as np
import pandas as pd
import pytest

from app.services.feature_engineering import FeatureEngineeringService, SlidingWindowBuffer
from ml.data_processing.batch_feature_pipeline import BatchFeaturePipeline, calculate_shannon_entropy


@pytest.fixture
def feature_service():
    service = FeatureEngineeringService()
    return service


def test_cold_start_features(feature_service):
    """Verify clean cold-start default features with zero NaNs or division by zero."""
    user_id = "user-new-001"
    features = feature_service.extract_features(user_id=user_id, amount=150.0, recipient_vpa="shop@upi")

    assert features["amount"] == 150.0
    assert features["txn_count_5m"] == 0.0
    assert features["txn_count_1h"] == 0.0
    assert features["txn_count_24h"] == 0.0
    assert features["amount_sum_5m"] == 0.0
    assert features["amount_sum_1h"] == 0.0
    assert features["delta_t_seconds"] == 86400.0  # Safe cold-start baseline
    assert features["recipient_entropy_1h"] == 0.0
    assert features["amount_deviation_ratio"] == 1.0  # Neutral baseline

    # Vector conversion check
    vec = feature_service.extract_feature_vector(user_id=user_id, amount=150.0)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (9,)
    assert not np.isnan(vec).any()
    assert not np.isinf(vec).any()


def test_sliding_window_counts_and_sums(feature_service):
    """Verify that transactions increment 5m, 1h, and 24h rolling windows correctly."""
    user_id = "user-velocity-002"
    base_t = 1700000000.0

    # Txn 1 at t=0
    feature_service.commit_transaction(user_id, amount=100.0, timestamp=base_t, recipient_vpa="merchantA@upi")

    # Txn 2 at t=60s (1 min later)
    f2 = feature_service.extract_features(user_id, amount=200.0, timestamp=base_t + 60.0, recipient_vpa="merchantB@upi")
    assert f2["txn_count_5m"] == 1.0
    assert f2["amount_sum_5m"] == 100.0
    assert f2["delta_t_seconds"] == 60.0
    feature_service.commit_transaction(user_id, amount=200.0, timestamp=base_t + 60.0, recipient_vpa="merchantB@upi")

    # Txn 3 at t=120s (2 min later)
    f3 = feature_service.extract_features(user_id, amount=300.0, timestamp=base_t + 120.0, recipient_vpa="merchantC@upi")
    assert f3["txn_count_5m"] == 2.0
    assert f3["amount_sum_5m"] == 300.0
    assert f3["delta_t_seconds"] == 60.0
    feature_service.commit_transaction(user_id, amount=300.0, timestamp=base_t + 120.0, recipient_vpa="merchantC@upi")


def test_window_expiration(feature_service):
    """Verify that transactions older than 5m drop out of 5m window but stay in 1h window."""
    user_id = "user-window-003"
    base_t = 1700000000.0

    # Txn 1 at t=0
    feature_service.commit_transaction(user_id, amount=100.0, timestamp=base_t, recipient_vpa="tea@upi")

    # Txn 2 at t=400s (6.67 minutes later - outside 5m window, inside 1h window)
    f2 = feature_service.extract_features(user_id, amount=150.0, timestamp=base_t + 400.0, recipient_vpa="tea@upi")
    assert f2["txn_count_5m"] == 0.0
    assert f2["amount_sum_5m"] == 0.0
    assert f2["txn_count_1h"] == 1.0
    assert f2["amount_sum_1h"] == 100.0
    assert f2["delta_t_seconds"] == 400.0

    # Txn 3 at t=4000s (outside 1h window, inside 24h window)
    f3 = feature_service.extract_features(user_id, amount=200.0, timestamp=base_t + 4000.0, recipient_vpa="tea@upi")
    assert f3["txn_count_5m"] == 0.0
    assert f3["txn_count_1h"] == 0.0
    assert f3["txn_count_24h"] == 1.0


def test_shannon_entropy_math():
    """Verify Shannon entropy correctly isolates fan-out / recipient switching behavior."""
    # Single recipient: H = 0.0
    assert calculate_shannon_entropy(["vendor@upi", "vendor@upi", "vendor@upi"]) == 0.0

    # 4 distinct recipients: H = - 4 * (0.25 * log2(0.25)) = 2.0
    diverse = ["v1@upi", "v2@upi", "v3@upi", "v4@upi"]
    assert calculate_shannon_entropy(diverse) == 2.0

    # Empty: H = 0.0
    assert calculate_shannon_entropy([]) == 0.0


def test_zero_future_leakage(feature_service):
    """Verify that extracting features does not mutate state until committed."""
    user_id = "user-leakage-004"
    t_now = 1700000000.0

    # Calling extract multiple times without commit must yield identical results
    res1 = feature_service.extract_features(user_id, amount=100.0, timestamp=t_now)
    res2 = feature_service.extract_features(user_id, amount=100.0, timestamp=t_now)
    assert res1 == res2
    assert res1["txn_count_5m"] == 0.0

    # After commit, subsequent extraction should see exactly 1 prior transaction
    feature_service.commit_transaction(user_id, amount=100.0, timestamp=t_now)
    res3 = feature_service.extract_features(user_id, amount=200.0, timestamp=t_now + 10.0)
    assert res3["txn_count_5m"] == 1.0


def test_batch_and_realtime_consistency():
    """Verify that offline batch feature extraction produces identical results to online streaming."""
    user_id = "user-parity-005"
    records = [
        {"user_id": user_id, "amount": 100.0, "timestamp": "2026-10-01T10:00:00Z", "recipient_vpa": "rec1@upi"},
        {"user_id": user_id, "amount": 250.0, "timestamp": "2026-10-01T10:02:00Z", "recipient_vpa": "rec2@upi"},
        {"user_id": user_id, "amount": 400.0, "timestamp": "2026-10-01T10:04:00Z", "recipient_vpa": "rec3@upi"},
    ]
    df_raw = pd.DataFrame(records)

    # 1. Batch pipeline
    pipeline = BatchFeaturePipeline()
    batch_features = pipeline.transform(df_raw)

    # 2. Real-time streaming service
    service = FeatureEngineeringService()
    streaming_features = []
    for _, row in df_raw.iterrows():
        dt = pd.to_datetime(row["timestamp"])
        f = service.extract_features(
            user_id=row["user_id"],
            amount=row["amount"],
            timestamp=dt,
            recipient_vpa=row["recipient_vpa"],
        )
        streaming_features.append(f)
        service.commit_transaction(
            user_id=row["user_id"],
            amount=row["amount"],
            timestamp=dt,
            recipient_vpa=row["recipient_vpa"],
        )

    df_streaming = pd.DataFrame(streaming_features)

    # Compare columns
    for col in BatchFeaturePipeline().feature_names:
        np.testing.assert_allclose(
            batch_features[col].values,
            df_streaming[col].values,
            rtol=1e-3,
            atol=1e-3,
            err_msg=f"Discrepancy in column {col}",
        )


def test_feature_extraction_latency_budget(feature_service):
    """Verify that feature vector generation satisfies the sub-10ms latency requirement."""
    user_id = "user-perf-006"
    base_t = 1700000000.0

    # Prime buffer with 20 past transactions
    for i in range(20):
        feature_service.commit_transaction(user_id, amount=50.0 + i, timestamp=base_t + i * 30, recipient_vpa=f"m{i % 4}@upi")

    # Measure latency across 1000 extractions
    latencies = []
    t_eval = base_t + 1000.0
    for _ in range(1000):
        start = time.perf_counter()
        _ = feature_service.extract_feature_vector(user_id, amount=250.0, timestamp=t_eval, recipient_vpa="m1@upi")
        latencies.append((time.perf_counter() - start) * 1000.0)  # ms

    p95_latency = np.percentile(latencies, 95)
    mean_latency = np.mean(latencies)

    # Requirement from synopsis: Feature vector generated in < 10ms
    assert p95_latency < 10.0, f"p95 latency {p95_latency:.3f}ms exceeded 10ms budget"
    assert mean_latency < 2.0, f"Mean latency {mean_latency:.3f}ms too high"
