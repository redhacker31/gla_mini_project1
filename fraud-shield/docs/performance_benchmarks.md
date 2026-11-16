# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-16T09:48:43.937338+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `18.377 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `15.172 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `31.62 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.05 | 0.08 | 0.06 | 0.13 | 0.21 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 6.45 | 8.06 | 7.83 | 9.61 | 10.01 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.05 | 0.08 | 0.07 | 0.13 | 0.14 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 4.41 | 6.95 | 6.38 | 9.66 | 15.76 | **PASSED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 12.07 | 15.17 | 14.54 | 18.38 | 23.86 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **44.6 req/s** | 9.94 | 17.05 | 20.68 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
