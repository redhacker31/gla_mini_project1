# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-16T09:32:43.834760+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `19.94 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `15.693 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `30.06 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.05 | 0.07 | 0.08 | 0.10 | 0.11 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 7.24 | 8.09 | 8.03 | 9.48 | 9.79 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.05 | 0.07 | 0.07 | 0.09 | 0.10 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 4.05 | 7.46 | 6.97 | 11.88 | 13.56 | **EXCEEDED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 11.92 | 15.69 | 15.86 | 19.94 | 21.38 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **44.3 req/s** | 10.03 | 14.95 | 18.62 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
