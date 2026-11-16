"""Performance Benchmarking & Sub-50ms SLA Concurrency Test Suite."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.benchmark_service import benchmark_service

client = TestClient(app)


def test_sub_50ms_sla_profile():
    """Verify that all pipeline components strictly adhere to sub-50ms latency budgets."""
    metrics, e2e_latencies = benchmark_service.profile_components(iterations=30)
    assert len(metrics) == 5

    metric_map = {m.component: m for m in metrics}

    # 1. Feature Extraction Budget <= 10.0ms
    fe_metric = metric_map["Feature Extraction"]
    assert fe_metric.mean_ms < 10.0, f"Feature extraction mean ({fe_metric.mean_ms}ms) exceeded 10ms budget"

    # 2. Isolation Forest Inference Budget <= 15.0ms
    ml_metric = metric_map["Isolation Forest ML"]
    assert ml_metric.mean_ms < 15.0, f"ML inference mean ({ml_metric.mean_ms}ms) exceeded 15ms budget"

    # 3. Rules & Sigmoid Fusion Budget <= 5.0ms
    rf_metric = metric_map["Rule Engine & Sigmoid Fusion"]
    assert rf_metric.mean_ms < 5.0, f"Rule engine mean ({rf_metric.mean_ms}ms) exceeded 5ms budget"

    # 4. End-to-End Pipeline Hard Budget <= 50.0ms
    e2e_metric = metric_map["End-to-End Gateway Pipeline"]
    assert e2e_metric.p95_ms <= 50.0, f"End-to-end p95 ({e2e_metric.p95_ms}ms) breached 50ms SLA ceiling"
    assert e2e_metric.sla_compliant is True


def test_concurrency_load_scaling():
    """Verify that concurrent micro-transaction bursts maintain sub-50ms latency with zero dropped requests."""
    concurrency_results = benchmark_service.benchmark_concurrency(
        concurrency_levels=[10, 25],
        requests_per_level=30,
    )

    assert len(concurrency_results) == 2

    for res in concurrency_results:
        # Zero error rate
        assert res.failed_requests == 0
        assert res.successful_requests == res.total_requests

        # Concurrency throughput should exceed 20 RPS on commodity CPU
        assert res.throughput_rps > 20.0, f"Throughput ({res.throughput_rps} RPS) too low for {res.concurrency_level} workers"

        # Concurrency p95 latency must respect SLA budget
        assert res.p95_latency_ms <= 50.0, f"Concurrency p95 ({res.p95_latency_ms}ms) exceeded 50ms for {res.concurrency_level} workers"
        assert res.sla_compliant is True


def test_benchmark_api_endpoints():
    """Verify GET /api/v1/system/benchmark/latest and POST /api/v1/system/benchmark/run endpoints."""
    # 1. Test GET latest report
    get_resp = client.get(f"{settings.API_V1_STR}/system/benchmark/latest")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["sla_target_ms"] == 50.0
    assert "overall_p95_latency_ms" in data
    assert "components" in data
    assert len(data["components"]) == 5
    assert "concurrency_benchmarks" in data

    # 2. Test POST run benchmark
    run_resp = client.post(
        f"{settings.API_V1_STR}/system/benchmark/run",
        json={"iterations": 20, "concurrency_levels": [10]},
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["sla_met"] is True
    assert run_data["overall_p95_latency_ms"] <= 50.0


def test_benchmark_artifacts_generated():
    """Verify that visualization plot and JSON reports are generated on disk."""
    report = benchmark_service.run_full_benchmark(iterations=20, concurrency_levels=[10])
    assert report.plot_artifact_path is not None
    assert os.path.exists(report.plot_artifact_path)
    assert os.path.getsize(report.plot_artifact_path) > 10000  # Non-empty PNG
