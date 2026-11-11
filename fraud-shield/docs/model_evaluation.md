# Fraud Shield — Model Evaluation Framework

## Objectives
- **Target PR-AUC**: $\ge 0.75$ on imbalanced test benchmark (< 0.2% fraud).
- **Target Recall**: $\ge 75\%$ at False Positive Rate (FPR) $\le 1.0\%$.
- **Latency Budget**: $p95 \le 25\text{ms}$ model inference, $p95 \le 50\text{ms}$ total API roundtrip.

## Benchmark Datasets
1. **PaySim Mobile Money**: Simulated mobile financial transactions based on sample of real logs.
2. **ULB Credit Card Fraud Detection**: European cardholder transactions exhibiting extreme class imbalance.

*Actual measured metrics will be populated during Phase 4 and Phase 12.*

