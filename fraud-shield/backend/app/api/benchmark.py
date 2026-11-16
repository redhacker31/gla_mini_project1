"""Performance Benchmarking & Sub-50ms SLA Concurrency Profiling Endpoints.

Provides endpoints to inspect component latency breakdowns, concurrency throughput,
and trigger on-demand SLA verification benchmark runs.
"""
from fastapi import APIRouter, HTTPException, status

from app.schemas.benchmark import (
    BenchmarkReportResponse,
    BenchmarkRunRequest,
)
from app.services.benchmark_service import benchmark_service

router = APIRouter()


@router.get(
    "/latest",
    response_model=BenchmarkReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Latest Performance & Concurrency Benchmark Report",
    description=(
        "Returns the latest empirical benchmark report, including component latency breakdown "
        "(Feature Extraction, Isolation Forest, Rules, Persistence) and concurrency throughput scaling."
    ),
)
async def get_latest_benchmark_report() -> BenchmarkReportResponse:
    """Fetch latest benchmark report."""
    try:
        return benchmark_service.get_latest_report()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve benchmark report: {str(exc)}",
        )


@router.post(
    "/run",
    response_model=BenchmarkReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Fresh Sub-50ms SLA Benchmark Run",
    description=(
        "Executes fresh end-to-end latency profiling across all pipeline components "
        "and profiles throughput across requested concurrency levels. Updates visual artifacts."
    ),
)
async def run_performance_benchmark(payload: BenchmarkRunRequest = BenchmarkRunRequest()) -> BenchmarkReportResponse:
    """Execute live latency and concurrency benchmark."""
    try:
        report = benchmark_service.run_full_benchmark(
            iterations=payload.iterations,
            concurrency_levels=payload.concurrency_levels,
        )
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(exc)}",
        )
