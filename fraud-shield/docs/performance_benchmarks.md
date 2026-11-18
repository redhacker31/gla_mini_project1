# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-18T05:51:02.638644+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `13.871 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `10.952 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `36.13 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.04 | 0.05 | 0.05 | 0.06 | 0.06 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 5.05 | 6.12 | 5.97 | 7.75 | 8.20 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.05 | 0.06 | 0.06 | 0.08 | 0.09 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 2.44 | 4.72 | 4.28 | 6.87 | 8.46 | **PASSED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 8.95 | 10.95 | 10.17 | 13.87 | 14.90 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **65.2 req/s** | 6.20 | 9.96 | 12.77 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
