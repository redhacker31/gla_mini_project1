# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-25T05:40:46.386244+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `36.702 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `20.282 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `13.3 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.06 | 0.07 | 0.08 | 0.09 | 0.09 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 6.76 | 11.93 | 11.42 | 15.96 | 21.20 | **EXCEEDED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.06 | 0.08 | 0.07 | 0.16 | 0.17 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 0.10 | 8.26 | 6.78 | 28.29 | 28.45 | **EXCEEDED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 13.68 | 20.28 | 18.76 | 36.70 | 37.49 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **47.8 req/s** | 10.53 | 25.52 | 28.24 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
