"""Pydantic schemas for System Performance & Concurrency Benchmarking."""
from typing import List, Optional
from pydantic import BaseModel, Field


class ComponentLatencyMetric(BaseModel):
    """Latency distribution for an individual pipeline subcomponent."""
    component: str = Field(..., description="Pipeline component name")
    budget_ms: float = Field(..., description="Target SLA latency budget ceiling in milliseconds")
    min_ms: float = Field(..., description="Minimum recorded execution time in ms")
    mean_ms: float = Field(..., description="Mean execution time in ms")
    median_ms: float = Field(..., description="50th percentile (median) execution time in ms")
    p95_ms: float = Field(..., description="95th percentile execution time in ms")
    p99_ms: float = Field(..., description="99th percentile execution time in ms")
    max_ms: float = Field(..., description="Maximum recorded execution time in ms")
    sla_compliant: bool = Field(..., description="True if p95 latency is within budget")


class ConcurrencyBenchmarkResult(BaseModel):
    """Performance metrics under multi-threaded / concurrent request load."""
    concurrency_level: int = Field(..., description="Concurrent virtual clients / threads")
    total_requests: int = Field(..., description="Total synthetic micro-transactions evaluated")
    successful_requests: int = Field(..., description="Successfully scored and persisted transactions")
    failed_requests: int = Field(..., description="Failed or timed-out requests")
    duration_seconds: float = Field(..., description="Total wall-clock duration in seconds")
    throughput_rps: float = Field(..., description="Throughput in requests per second (RPS)")
    p50_latency_ms: float = Field(..., description="Median latency under concurrency")
    p95_latency_ms: float = Field(..., description="95th percentile latency under concurrency")
    p99_latency_ms: float = Field(..., description="99th percentile latency under concurrency")
    sla_compliant: bool = Field(..., description="True if p95 latency is <= 50.0ms")


class BenchmarkReportResponse(BaseModel):
    """Complete latency profiling and concurrency benchmark report."""
    timestamp: str = Field(..., description="Benchmark execution timestamp in ISO-8601 UTC")
    environment: str = Field(..., description="Execution environment (commodity CPU)")
    overall_p95_latency_ms: float = Field(..., description="End-to-end p95 evaluation latency in ms")
    overall_mean_latency_ms: float = Field(..., description="End-to-end mean evaluation latency in ms")
    sla_target_ms: float = Field(default=50.0, description="Strict SLA ceiling in ms (50.0ms)")
    sla_met: bool = Field(..., description="True if end-to-end p95 is strictly <= 50.0ms")
    components: List[ComponentLatencyMetric] = Field(..., description="Component-level latency breakdowns")
    concurrency_benchmarks: List[ConcurrencyBenchmarkResult] = Field(..., description="Concurrency stress levels")
    plot_artifact_path: Optional[str] = Field(default=None, description="Path to generated visualization plot")


class BenchmarkRunRequest(BaseModel):
    """Request payload to initiate on-demand performance benchmarking."""
    iterations: int = Field(default=100, ge=10, le=500, description="Iterations for component latency profiling")
    concurrency_levels: List[int] = Field(default=[10, 25, 50], description="Concurrency levels to benchmark")
