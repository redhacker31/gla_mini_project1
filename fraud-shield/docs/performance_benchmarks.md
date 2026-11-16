# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-16T09:23:47.105177+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `24.446 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `17.382 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `25.55 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.06 | 0.08 | 0.08 | 0.12 | 0.15 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 7.48 | 10.06 | 9.62 | 13.47 | 13.79 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.05 | 0.10 | 0.08 | 0.14 | 0.42 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 0.12 | 7.14 | 6.79 | 13.98 | 15.88 | **EXCEEDED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 12.68 | 17.38 | 17.43 | 24.45 | 24.84 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **47.6 req/s** | 9.84 | 15.80 | 18.85 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
