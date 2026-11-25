# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-25T06:03:09.294154+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `18.523 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `14.029 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `31.48 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.05 | 0.07 | 0.07 | 0.10 | 0.16 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 6.03 | 7.81 | 7.60 | 9.72 | 10.55 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.02 | 0.06 | 0.05 | 0.10 | 0.12 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 2.85 | 6.09 | 5.54 | 10.62 | 12.02 | **EXCEEDED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 11.08 | 14.03 | 13.29 | 18.52 | 19.50 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **72.5 req/s** | 9.14 | 14.06 | 18.14 | **PASSED** |
| **25 Workers** | 50 | **69.0 req/s** | 10.26 | 21.08 | 25.04 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
