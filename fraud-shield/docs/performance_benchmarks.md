# Fraud Shield — Performance Benchmarking & Sub-50ms SLA Concurrency Profile

**Report Generated:** 2026-11-25T06:10:39.581224+00:00  
**Execution Environment:** Commodity x86_64 CPU (Local SQLite WAL Mode)  
**SLA Compliance Status:** PASSED (Sub-50ms Compliant)  

---

## 1. Executive Summary
- **Measured End-to-End p95 Latency:** `13.719 ms` (Target: `<= 50.0 ms`).
- **Measured End-to-End Mean Latency:** `11.591 ms`.
- **SLA Budget Ceiling:** `50.0 ms`.
- **Target SLA Margin:** `36.28 ms` buffer beneath maximum threshold.

---

## 2. Pipeline Subcomponent Latency Breakdown

| Component | Budget Ceiling | Min (ms) | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | SLA Status |
|---|---|---|---|---|---|---|---|
| **Feature Extraction** | `10.0 ms` | 0.05 | 0.06 | 0.06 | 0.09 | 0.11 | **PASSED** |
| **Isolation Forest ML** | `15.0 ms` | 5.32 | 6.69 | 6.73 | 8.35 | 8.48 | **PASSED** |
| **Rule Engine & Sigmoid Fusion** | `5.0 ms` | 0.04 | 0.06 | 0.05 | 0.08 | 0.09 | **PASSED** |
| **Persistence & Audit Chaining** | `10.0 ms` | 1.16 | 4.78 | 4.32 | 7.45 | 16.33 | **PASSED** |
| **End-to-End Gateway Pipeline** | `50.0 ms` | 8.49 | 11.59 | 11.19 | 13.72 | 22.10 | **PASSED** |

---

## 3. Concurrency Stress Profiling

| Concurrency (Clients) | Total Requests | Throughput (RPS) | Median (ms) | p95 (ms) | p99 (ms) | SLA Compliance |
|---|---|---|---|---|---|---|
| **10 Workers** | 50 | **82.9 req/s** | 7.09 | 10.47 | 12.34 | **PASSED** |
| **25 Workers** | 50 | **78.7 req/s** | 8.07 | 16.75 | 21.93 | **PASSED** |

---

## 4. Visual Artifacts
- **Benchmark Plot Artifact:** Saved to [`ml/artifacts/performance_benchmark_plot.png`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_plot.png).
- **JSON Report:** Serialized to [`ml/artifacts/performance_benchmark_report.json`](file:///D:/projects/3rd%20sem%20mini%20project/fraud-shield/ml/artifacts/performance_benchmark_report.json).
