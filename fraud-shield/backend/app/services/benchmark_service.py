"""Performance Benchmarking & Sub-50ms Concurrency Profiling Service.

Profiles end-to-end transaction ingestion, feature extraction, Isolation Forest inference,
deterministic rule fusion, SQLite WAL persistence, and cryptographic audit hashing.
Generates empirical SLA compliance reports and multi-panel visualization plots.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.config import settings
from app.database.session import get_db_context
from app.schemas.benchmark import (
    BenchmarkReportResponse,
    ComponentLatencyMetric,
    ConcurrencyBenchmarkResult,
)
from app.schemas.transaction import TransactionEvaluateRequest
from app.services.anomaly_detector import anomaly_detector_service
from app.services.feature_engineering import feature_service
from app.services.risk_engine import risk_engine_service
from app.services.transaction_service import transaction_service


class BenchmarkService:
    """Orchestrates latency profiling, concurrency stress testing, and visual artifact export."""

    COMPONENT_BUDGETS: Dict[str, float] = {
        "Feature Extraction": 10.0,
        "Isolation Forest ML": 15.0,
        "Rule Engine & Sigmoid Fusion": 5.0,
        "Persistence & Audit Chaining": 10.0,
        "End-to-End Gateway Pipeline": 50.0,
    }

    def __init__(self):
        self._cached_report: Optional[BenchmarkReportResponse] = None

    def _resolve_artifact_dir(self) -> str:
        """Find valid path to ml/artifacts directory."""
        candidates = [
            os.path.abspath("ml/artifacts"),
            os.path.abspath("../ml/artifacts"),
            os.path.abspath("../../ml/artifacts"),
            os.path.abspath("fraud-shield/ml/artifacts"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        # Default fallback
        os.makedirs("ml/artifacts", exist_ok=True)
        return os.path.abspath("ml/artifacts")

    def _resolve_docs_dir(self) -> str:
        """Find valid path to docs directory."""
        candidates = [
            os.path.abspath("docs"),
            os.path.abspath("../docs"),
            os.path.abspath("../../docs"),
            os.path.abspath("fraud-shield/docs"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        os.makedirs("docs", exist_ok=True)
        return os.path.abspath("docs")

    def profile_components(self, iterations: int = 100) -> Tuple[List[ComponentLatencyMetric], List[float]]:
        """Profile execution latency for each subcomponent across N iterations."""
        feature_latencies = []
        ml_latencies = []
        rule_latencies = []
        persist_latencies = []
        e2e_latencies = []

        # Warm-up phase
        warmup_req = TransactionEvaluateRequest(
            user_id="warmup_benchmark_user",
            amount=150.0,
            recipient_vpa="store@paytm",
            merchant_category="grocery",
            channel="UPI_APP",
        )
        for _ in range(5):
            with get_db_context() as db:
                _ = transaction_service.evaluate_transaction(warmup_req, db=db)

        # Execution iterations
        for i in range(iterations):
            uid = f"bench_user_{(i % 10) + 1}"
            amt = 50.0 + (i * 7.5) % 850.0
            vpa = f"merchant_{(i % 5) + 1}@upi"
            now = datetime.now(timezone.utc)

            # 1. Feature Extraction
            t0 = time.perf_counter()
            features = feature_service.extract_features(uid, amt, now, vpa)
            feature_vector = feature_service.extract_feature_vector(uid, amt, now, vpa)
            t1 = time.perf_counter()
            feature_latencies.append((t1 - t0) * 1000.0)

            # 2. Isolation Forest ML
            t1_ml = time.perf_counter()
            ml_score = anomaly_detector_service.predict_anomaly_score(feature_vector)
            t2 = time.perf_counter()
            ml_latencies.append((t2 - t1_ml) * 1000.0)

            # 3. Rule Engine & Sigmoid Fusion
            t2_rules = time.perf_counter()
            decision = risk_engine_service.evaluate(
                ml_score=ml_score,
                features=features,
                recipient_vpa=vpa,
                failed_otp_attempts=0,
            )
            t3 = time.perf_counter()
            rule_latencies.append((t3 - t2_rules) * 1000.0)

            # 4. End-to-End Pipeline with Persistence & Audit Chaining
            req = TransactionEvaluateRequest(
                user_id=uid,
                amount=round(amt, 2),
                recipient_vpa=vpa,
                merchant_category="grocery",
                channel="UPI_APP",
            )
            t4_e2e = time.perf_counter()
            with get_db_context() as db:
                resp = transaction_service.evaluate_transaction(req, db=db)
            t5_e2e = time.perf_counter()

            e2e_lat = (t5_e2e - t4_e2e) * 1000.0
            e2e_latencies.append(e2e_lat)
            # Implied persistence time
            persist_time = max(0.1, e2e_lat - ((t1 - t0) + (t2 - t1_ml) + (t3 - t2_rules)) * 1000.0)
            persist_latencies.append(persist_time)

        # Statistical summaries
        def compute_metrics(name: str, values: List[float], budget: float) -> ComponentLatencyMetric:
            arr = np.array(values)
            p95 = float(np.percentile(arr, 95))
            return ComponentLatencyMetric(
                component=name,
                budget_ms=budget,
                min_ms=round(float(np.min(arr)), 3),
                mean_ms=round(float(np.mean(arr)), 3),
                median_ms=round(float(np.median(arr)), 3),
                p95_ms=round(p95, 3),
                p99_ms=round(float(np.percentile(arr, 99)), 3),
                max_ms=round(float(np.max(arr)), 3),
                sla_compliant=p95 <= budget,
            )

        metrics = [
            compute_metrics("Feature Extraction", feature_latencies, self.COMPONENT_BUDGETS["Feature Extraction"]),
            compute_metrics("Isolation Forest ML", ml_latencies, self.COMPONENT_BUDGETS["Isolation Forest ML"]),
            compute_metrics("Rule Engine & Sigmoid Fusion", rule_latencies, self.COMPONENT_BUDGETS["Rule Engine & Sigmoid Fusion"]),
            compute_metrics("Persistence & Audit Chaining", persist_latencies, self.COMPONENT_BUDGETS["Persistence & Audit Chaining"]),
            compute_metrics("End-to-End Gateway Pipeline", e2e_latencies, self.COMPONENT_BUDGETS["End-to-End Gateway Pipeline"]),
        ]

        return metrics, e2e_latencies

    def benchmark_concurrency(
        self,
        concurrency_levels: List[int] = [10, 25, 50],
        requests_per_level: int = 50,
    ) -> List[ConcurrencyBenchmarkResult]:
        """Profile throughput and latency under multi-threaded concurrent load."""
        results: List[ConcurrencyBenchmarkResult] = []

        # Pre-seed concurrent test accounts to initialize SQLite user records
        for u_idx in range(8):
            seed_req = TransactionEvaluateRequest(
                user_id=f"concurrent_user_{u_idx}",
                amount=100.0,
                recipient_vpa="seed@upi",
                merchant_category="miscellaneous",
                channel="UPI_APP",
            )
            with get_db_context() as db:
                _ = transaction_service.evaluate_transaction(seed_req, db=db)

        def execute_single_txn(idx: int) -> float:
            req = TransactionEvaluateRequest(
                user_id=f"concurrent_user_{idx % 8}",
                amount=round(50.0 + (idx * 5.0) % 900.0, 2),
                recipient_vpa=f"payee_{(idx % 4) + 1}@upi",
                merchant_category="miscellaneous",
                channel="UPI_APP",
            )
            with get_db_context() as db:
                resp = transaction_service.evaluate_transaction(req, db=db)
            return float(resp.latency_ms)

        for concurrency in concurrency_levels:
            total_reqs = max(requests_per_level, concurrency * 2)
            latencies = []
            failures = 0

            t_start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(execute_single_txn, i) for i in range(total_reqs)]
                for fut in as_completed(futures):
                    try:
                        lat = fut.result()
                        latencies.append(lat)
                    except Exception:
                        failures += 1

            t_end = time.perf_counter()
            duration = max(0.001, t_end - t_start)
            throughput = len(latencies) / duration

            lat_arr = np.array(latencies) if latencies else np.array([0.0])
            p50 = float(np.percentile(lat_arr, 50))
            p95 = float(np.percentile(lat_arr, 95))
            p99 = float(np.percentile(lat_arr, 99))

            results.append(
                ConcurrencyBenchmarkResult(
                    concurrency_level=concurrency,
                    total_requests=total_reqs,
                    successful_requests=len(latencies),
                    failed_requests=failures,
                    duration_seconds=round(duration, 3),
                    throughput_rps=round(throughput, 1),
                    p50_latency_ms=round(p50, 2),
                    p95_latency_ms=round(p95, 2),
                    p99_latency_ms=round(p99, 2),
                    sla_compliant=p95 <= 50.0,
                )
            )

        return results

    def generate_visualization(
        self,
        component_metrics: List[ComponentLatencyMetric],
        e2e_latencies: List[float],
        concurrency_results: List[ConcurrencyBenchmarkResult],
        output_path: str,
    ):
        """Generate multi-panel performance visualization plot using headless matplotlib."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.style.use("dark_background")
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            "Fraud Shield — End-to-End Latency & Concurrency Benchmarks (SLA Target <= 50ms)",
            fontsize=15,
            fontweight="bold",
            color="#38bdf8",
            y=0.98,
        )

        # Subplot 1: Component Latencies vs Budgets
        ax1 = axes[0, 0]
        comp_names = [m.component for m in component_metrics if m.component != "End-to-End Gateway Pipeline"]
        means = [m.mean_ms for m in component_metrics if m.component != "End-to-End Gateway Pipeline"]
        p95s = [m.p95_ms for m in component_metrics if m.component != "End-to-End Gateway Pipeline"]
        budgets = [m.budget_ms for m in component_metrics if m.component != "End-to-End Gateway Pipeline"]

        y = np.arange(len(comp_names))
        height = 0.35

        ax1.barh(y - height/2, means, height, label="Mean Latency (ms)", color="#38bdf8", alpha=0.9)
        ax1.barh(y + height/2, p95s, height, label="p95 Latency (ms)", color="#a855f7", alpha=0.9)
        ax1.scatter(budgets, y, color="#ef4444", zorder=5, label="SLA Budget Ceiling", s=70, marker="x")

        ax1.set_yticks(y)
        ax1.set_yticklabels(comp_names, fontsize=9)
        ax1.set_xlabel("Latency (ms)", fontsize=10)
        ax1.set_title("Component Latency Profile vs Sub-Budgets", fontsize=11, fontweight="bold")
        ax1.legend(loc="lower right", fontsize=8)
        ax1.grid(axis="x", linestyle="--", alpha=0.3)

        # Subplot 2: End-to-End Latency Distribution Histogram
        ax2 = axes[0, 1]
        lat_arr = np.array(e2e_latencies)
        ax2.hist(lat_arr, bins=25, color="#10b981", alpha=0.75, edgecolor="#047857", density=True)
        p95_val = float(np.percentile(lat_arr, 95))
        mean_val = float(np.mean(lat_arr))

        ax2.axvline(p95_val, color="#a855f7", linestyle="--", linewidth=2, label=f"p95: {p95_val:.2f}ms")
        ax2.axvline(mean_val, color="#38bdf8", linestyle="-", linewidth=2, label=f"Mean: {mean_val:.2f}ms")
        ax2.axvline(50.0, color="#ef4444", linestyle=":", linewidth=2, label="Hard SLA Budget: 50.0ms")

        ax2.set_xlabel("End-to-End Latency (ms)", fontsize=10)
        ax2.set_ylabel("Probability Density", fontsize=10)
        ax2.set_title("End-to-End Gateway Latency Distribution", fontsize=11, fontweight="bold")
        ax2.legend(loc="upper right", fontsize=8)
        ax2.grid(linestyle="--", alpha=0.3)

        # Subplot 3: Empirical Cumulative Distribution Function (ECDF)
        ax3 = axes[1, 0]
        sorted_lats = np.sort(lat_arr)
        ecdf = np.arange(1, len(sorted_lats) + 1) / len(sorted_lats)

        ax3.plot(sorted_lats, ecdf, color="#34d399", linewidth=2.5, label="Empirical CDF")
        ax3.axhline(0.95, color="#a855f7", linestyle="--", label="95th Percentile")
        ax3.axvline(50.0, color="#ef4444", linestyle=":", label="SLA Budget Limit (50ms)")

        # Target annotation
        compliance_pct = float(np.mean(lat_arr <= 50.0) * 100)
        ax3.text(
            sorted_lats[len(sorted_lats)//2],
            0.5,
            f"SLA Compliance: {compliance_pct:.1f}%\n(P(Latency <= 50ms))",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#1e293b", edgecolor="#10b981"),
            fontsize=9,
            color="#34d399",
        )

        ax3.set_xlabel("Latency (ms)", fontsize=10)
        ax3.set_ylabel("P(Execution Time <= t)", fontsize=10)
        ax3.set_title("Empirical Cumulative Distribution Function (ECDF)", fontsize=11, fontweight="bold")
        ax3.set_ylim(-0.05, 1.05)
        ax3.legend(loc="lower right", fontsize=8)
        ax3.grid(linestyle="--", alpha=0.3)

        # Subplot 4: Concurrency Throughput (RPS) vs Concurrency Level
        ax4 = axes[1, 1]
        levels = [c.concurrency_level for c in concurrency_results]
        throughput = [c.throughput_rps for c in concurrency_results]
        p95_conc = [c.p95_latency_ms for c in concurrency_results]

        color1 = "#38bdf8"
        color2 = "#f59e0b"

        ax4.bar(levels, throughput, width=5, color=color1, alpha=0.85, label="Throughput (RPS)")
        ax4.set_xlabel("Concurrency Level (Virtual Clients)", fontsize=10)
        ax4.set_ylabel("Throughput (Requests / Sec)", color=color1, fontsize=10)
        ax4.tick_params(axis="y", labelcolor=color1)

        ax4_twin = ax4.twinx()
        ax4_twin.plot(levels, p95_conc, color=color2, marker="o", linewidth=2, label="p95 Latency (ms)")
        ax4_twin.axhline(50.0, color="#ef4444", linestyle=":", label="50ms Ceiling")
        ax4_twin.set_ylabel("p95 Latency (ms)", color=color2, fontsize=10)
        ax4_twin.tick_params(axis="y", labelcolor=color2)

        ax4.set_title("Throughput & p95 Latency Scaling Under Concurrency", fontsize=11, fontweight="bold")
        ax4.grid(axis="x", linestyle="--", alpha=0.3)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=200)
        plt.close(fig)

    def run_full_benchmark(
        self,
        iterations: int = 100,
        concurrency_levels: List[int] = [10, 25, 50],
    ) -> BenchmarkReportResponse:
        """Run complete performance benchmark, write artifacts, and return report."""
        component_metrics, e2e_latencies = self.profile_components(iterations=iterations)
        concurrency_results = self.benchmark_concurrency(concurrency_levels=concurrency_levels)

        e2e_metric = next(m for m in component_metrics if m.component == "End-to-End Gateway Pipeline")
        p95_overall = e2e_metric.p95_ms
        mean_overall = e2e_metric.mean_ms
        sla_met = p95_overall <= 50.0

        artifact_dir = self._resolve_artifact_dir()
        plot_path = os.path.join(artifact_dir, "performance_benchmark_plot.png")
        report_json_path = os.path.join(artifact_dir, "performance_benchmark_report.json")

        self.generate_visualization(
            component_metrics=component_metrics,
            e2e_latencies=e2e_latencies,
            concurrency_results=concurrency_results,
            output_path=plot_path,
        )

        report = BenchmarkReportResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment="Commodity x86_64 CPU (Local SQLite WAL Mode)",
            overall_p95_latency_ms=p95_overall,
            overall_mean_latency_ms=mean_overall,
            sla_target_ms=50.0,
            sla_met=sla_met,
            components=component_metrics,
            concurrency_benchmarks=concurrency_results,
            plot_artifact_path=plot_path,
        )

        # Write JSON artifact
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        # Write Markdown documentation report
        docs_dir = self._resolve_docs_dir()
        doc_path = os.path.join(docs_dir, "performance_benchmarks.md")
        self._write_markdown_documentation(report, doc_path)

        self._cached_report = report
        return report

    def _write_markdown_documentation(self, report: BenchmarkReportResponse, doc_path: str):
        """Format and persist human-readable markdown documentation."""
        md_lines = [
            "# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile",
            "",
            f"**Report Generated:** {report.timestamp}  ",
            f"**Execution Environment:** {report.environment}  ",
            f"**SLA Compliance Status:** {'PASSED (Sub-50ms Compliant)' if report.sla_met else 'FAILED'}  ",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            f"- **Measured End-to-End p95 Latency:** `{report.overall_p95_latency_ms} ms` (Target: `<= 50.0 ms`).",
            f"- **Measured End-to-End Mean Latency:** `{report.overall_mean_latency_ms} ms`.",
            f"- **SLA Budget Ceiling:** `50.0 ms`.",
            f"- **Target SLA Margin:** `{round(50.0 - report.overall_p95_latency_ms, 2)} ms` buffer beneath maximum threshold.",
            "",
            "---",
            "",
            "## 2. Pipeline Subcomponent Latency Breakdown",
            "",
            "| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |",
            "|---|---|---|---|---|---|---|---|",
        ]

        for c in report.components:
            status = "PASSED" if c.sla_compliant else "EXCEEDED"
            md_lines.append(
                f"| **{c.component}** | `{c.budget_ms:.1f} ms` | {c.min_ms:.2f} | {c.mean_ms:.2f} | {c.median_ms:.2f} | {c.p95_ms:.2f} | {c.p99_ms:.2f} | **{status}** |"
            )

        md_lines.extend([
            "",
            "---",
            "",
            "## 3. Concurrency Stress Profiling",
            "",
            "| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |",
            "|---|---|---|---|---|---|---|",
        ])

        for conc in report.concurrency_benchmarks:
            c_status = "PASSED" if conc.sla_compliant else "EXCEEDED"
            md_lines.append(
                f"| **{conc.concurrency_level} Workers** | {conc.total_requests} | **{conc.throughput_rps:.1f} req/s** | {conc.p50_latency_ms:.2f} | {conc.p95_latency_ms:.2f} | {conc.p99_latency_ms:.2f} | **{c_status}** |"
            )

        md_lines.extend([
            "",
            "---",
            "",
            "## 4. Visual Artifacts",
            "- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).",
            "- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).",
            "",
        ])

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

    def get_latest_report(self) -> BenchmarkReportResponse:
        """Retrieve cached report or run default benchmark."""
        if self._cached_report is not None:
            return self._cached_report

        # Try to read from saved JSON
        artifact_dir = self._resolve_artifact_dir()
        report_json_path = os.path.join(artifact_dir, "performance_benchmark_report.json")
        if os.path.exists(report_json_path):
            try:
                with open(report_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cached_report = BenchmarkReportResponse(**data)
                    return self._cached_report
            except Exception:
                pass

        # If not present, run fresh benchmark
        return self.run_full_benchmark(iterations=50, concurrency_levels=[10, 25])


# Singleton instance
benchmark_service = BenchmarkService()
