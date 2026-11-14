"""Unit tests for Phase 4 Isolation Forest Model and Anomaly Detection Service."""
import os
import time
import numpy as np
import pytest

from app.services.anomaly_detector import AnomalyDetectorService
from ml.data_processing.batch_feature_pipeline import FEATURE_NAMES


@pytest.fixture
def anomaly_service():
    # Looks for serialized joblib artifact
    service = AnomalyDetectorService()
    return service


def test_model_artifact_exists_and_loads(anomaly_service):
    """Verify that the trained Isolation Forest bundle loads successfully."""
    assert anomaly_service.is_loaded is True
    assert anomaly_service.model is not None
    assert anomaly_service.scaler is not None
    assert anomaly_service.feature_names == FEATURE_NAMES


def test_score_normalization_bounds(anomaly_service):
    """Verify that all anomaly scores are strictly bounded within [0.0, 1.0]."""
    rng = np.random.default_rng(42)
    # Generate 50 random vectors
    random_vectors = rng.uniform(0.0, 1000.0, size=(50, len(FEATURE_NAMES))).astype(np.float32)

    for i in range(50):
        score = anomaly_service.predict_anomaly_score(random_vectors[i])
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0, f"Score {score} out of bounds!"


def test_routine_vs_velocity_burst_separation(anomaly_service):
    """Verify that routine transactions receive low scores and velocity bursts receive high scores."""
    # Routine grocery purchase (Ramesh persona): 150 INR, 0 prior txns in 5m, delta-t=24h, entropy=0, ratio=1.0
    routine_vector = np.array([
        150.0,   # amount
        0.0,     # count_5m
        0.0,     # count_1h
        1.0,     # count_24h
        0.0,     # sum_5m
        0.0,     # sum_1h
        86400.0, # delta_t
        0.0,     # entropy
        1.0,     # deviation ratio
    ], dtype=np.float32)

    # Velocity Burst Attack: 6th transaction in 2 minutes, delta-t=12s, high recipient entropy, high deviation
    burst_vector = np.array([
        490.0,   # amount (just under 500)
        5.0,     # count_5m
        8.0,     # count_1h
        12.0,    # count_24h
        2450.0,  # sum_5m
        3920.0,  # sum_1h
        12.0,    # delta_t (<15s)
        2.1,     # entropy (diverse mule accounts)
        2.8,     # deviation ratio
    ], dtype=np.float32)

    routine_score = anomaly_service.predict_anomaly_score(routine_vector)
    burst_score = anomaly_service.predict_anomaly_score(burst_vector)

    print(f"\nRoutine Score: {routine_score:.4f} | Burst Score: {burst_score:.4f}")
    assert routine_score < 0.45, f"Routine score {routine_score} unexpectedly high"
    assert burst_score > routine_score, "Burst attack must score strictly higher than routine transaction"
    assert burst_score >= 0.50, f"Burst score {burst_score} failed to be flagged as anomalous"


def test_single_sample_inference_latency_sla(anomaly_service):
    """Verify that single-sample inference complies with the sub-15ms budget."""
    sample = np.array([250.0, 1.0, 2.0, 3.0, 250.0, 500.0, 180.0, 0.5, 1.1], dtype=np.float32)

    # Warmup
    for _ in range(10):
        _ = anomaly_service.predict_anomaly_score(sample)

    latencies = []
    for _ in range(200):
        t0 = time.perf_counter()
        _ = anomaly_service.predict_anomaly_score(sample)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    p95 = np.percentile(latencies, 95)
    mean_lat = np.mean(latencies)
    assert p95 < 20.0, f"p95 inference latency {p95:.2f}ms exceeded 20ms target"
    assert mean_lat < 15.0, f"Mean latency {mean_lat:.2f}ms exceeded target"


def test_heuristic_fallback_service():
    """Verify that fallback heuristics operate cleanly when model file is absent."""
    service = AnomalyDetectorService(model_path="non_existent_file.joblib")
    assert service.is_loaded is False

    sample = np.array([450.0, 6.0, 10.0, 15.0, 2000.0, 4000.0, 15.0, 1.8, 2.0], dtype=np.float32)
    score = service.predict_anomaly_score(sample)
    assert 0.0 <= score <= 1.0
    assert score >= 0.60  # Fallback correctly detects burst indicators

