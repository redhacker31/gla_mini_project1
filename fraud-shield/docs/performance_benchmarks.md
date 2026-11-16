# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-16T09:13:22.104438+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `12.187 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `9.037 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `37.81 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.03 | 0.04 | 0.04 | 0.05 | 0.05 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 4.28 | 5.18 | 4.75 | 6.53 | 6.59 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.03 | 0.04 | 0.04 | 0.06 | 0.07 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 2.01 | 3.77 | 3.17 | 6.62 | 8.12 | **PASSED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 7.20 | 9.04 | 8.97 | 12.19 | 13.07 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **78.5 req/s** | 5.46 | 7.93 | 11.90 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
