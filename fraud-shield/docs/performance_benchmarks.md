# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-16T09:37:14.211699+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `21.498 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `12.296 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `28.5 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.03 | 0.05 | 0.05 | 0.08 | 0.09 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 4.48 | 6.24 | 6.02 | 8.42 | 9.89 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.04 | 0.08 | 0.07 | 0.11 | 0.22 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 2.59 | 5.93 | 5.06 | 13.75 | 13.85 | **EXCEEDED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 8.15 | 12.30 | 10.70 | 21.50 | 22.16 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **55.9 req/s** | 6.81 | 12.55 | 18.69 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
