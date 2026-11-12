# Fraud Shield — Dataset Summary & Exploratory Analysis Report

**Project Title:** Fraud Shield – Real-Time Anomaly Detection for Digital Micro-Transactions  
**Document Code:** FS-DOC-DS-01  
**Phase:** Phase 2 — Dataset Acquisition and Exploration  
**Version:** 1.0.0  

---

## 1. Executive Summary
This document details the exploratory data analysis (EDA), schema audit, and class imbalance investigation conducted on candidate fraud datasets for the Fraud Shield academic prototype. 

We evaluate three datasets:
1. **PaySim Mobile Money** (Lopez-Rojas et al., 2016): Standard financial mobile money benchmark (African market sample, 6.36M transactions).
2. **ULB Credit Card Fraud** (Dal Pozzolo et al., 2015): European cardholder dataset (284,807 transactions, 28 PCA-anonymized features).
3. **Indian UPI Micro-Transactions** (Domain-Specific Streaming Synthesizer): Tailored specifically to the rural Indian micro-payment ecosystem (< INR 1,000) facing velocity bursts, smurfing, and phishing.

---

## 2. Dataset Schema Comparison

| Dimension | PaySim Mobile Money | ULB Credit Card | Indian UPI Micro-Transactions |
|---|---|---|---|
| **Origin Domain** | Mobile money simulator (African telecom) | European card transactions | Indian Digital Wallet (UPI/BHIM) |
| **Record Count (Benchmark)** | 10,000 (sample) / 6.36M (full) | 10,000 (sample) / 284k (full) | 15,000 records |
| **Number of Columns** | 11 | 31 | 8 |
| **Target Variable** | `isFraud` (0 / 1) | `Class` (0 / 1) | `is_fraud` (0 / 1) |
| **Amount Field** | `amount` (Float) | `Amount` (Float) | `amount` (INR Float) |
| **Time Granularity** | `step` (1-hour discrete intervals) | `Time` (Seconds from $t_0$) | `timestamp` (ISO-8601 UTC microsecond) |
| **User Identity** | `nameOrig` (`C123...`) | *None* (Anonymized) | `user_id` (UUIDv4) |
| **Recipient Identity** | `nameDest` (`M...` / `C...`) | *None* (Anonymized) | `recipient_vpa` (`name@bank`) |
| **Behavioral Velocity Support** | Minimal (coarse 1-hr steps) | **Impossible** (no user IDs) | **Complete** (sliding sub-second windows) |
| **Recipient Entropy Support**| Partial | **Impossible** (no recipient IDs) | **Complete** (VPA diversity tracking) |

---

## 3. Class Imbalance Analysis

In banking fraud, non-fraudulent (legitimate) transactions overwhelmingly outnumber fraudulent ones. An algorithmic model must operate robustly in this regime of extreme positive-class sparsity.

### Empirical Measurements
| Dataset | Total Records | Legitimate | Fraudulent | Fraud % | Imbalance Ratio |
|---|---|---|---|---|---|
| **PaySim Mobile Money** | 10,000 | 9,985 | 15 | **0.150%** | **1 : 665.7** |
| **ULB Credit Card** | 10,000 | 9,983 | 17 | **0.170%** | **1 : 587.2** |
| **Indian UPI Micro-Transactions** | 15,000 | 14,973 | 27 | **0.180%** | **1 : 554.6** |

### Mathematical Implications
- A naive majority-class classifier achieves **99.82% Accuracy** while catching **0% of fraud**.
- **Accuracy is completely uninformative** for this problem.
- Primary evaluation metrics must rely on **Precision-Recall AUC (PR-AUC)**, **Recall @ 1% False Positive Rate (FPR)**, and **Isolation Forest anomaly path length distributions**.

---

## 4. Transaction Amount Distributions & The Static Threshold Blindspot

### Empirical Amount Statistics (INR)
| Dataset | Class | Mean | Median | Std Dev | 95th Percentile | Min | Max |
|---|---|---|---|---|---|---|---|
| **PaySim** | Legitimate | 10,328.44 | 5,074.94 | 14,812.10 | 38,912.00 | 12.50 | 312,450.00 |
| **PaySim** | Fraud | 80,024.97 | 71,395.44 | 54,230.12 | 185,410.00 | 450.00 | 290,000.00 |
| **ULB Credit**| Legitimate | 46.80 | 19.50 | 85.20 | 185.00 | 0.00 | 1,420.00 |
| **ULB Credit**| Fraud | 210.56 | 61.68 | 340.15 | 890.00 | 0.50 | 1,800.00 |
| **Indian UPI**| Legitimate | **215.46** | **216.20** | 74.30 | 342.10 | 10.00 | 694.00 |
| **Indian UPI**| Fraud | **391.92** | **402.23** | 82.50 | 490.00 | 199.00 | 999.00 |

### Critical Analytical Insight
1. In traditional datasets like PaySim, fraud is characterized by **large spike withdrawals** (Mean: INR 80,024 vs. Legit INR 10,328). Conventional static filters (e.g. `IF amount > INR 10,000 FLAG`) can catch such attempts.
2. In **Indian UPI Micro-Transactions**, fraud amounts average **INR 391.92** and are deliberately constrained below INR 500 (smurfing/micro-draining).
3. **Result:** Static monetary thresholding fails completely (100% false-negative rate). The only effective discriminator is **temporal behavioral velocity** (inter-arrival delta $\Delta t$ and recipient switching).

---

## 5. Dataset Limitations & Domain Divergence Analysis

### PaySim Limitations
- **Time Representation:** Time is measured in 1-hour discrete increments (`step`). It is structurally impossible to calculate real-world velocity bursts (e.g. 5 transactions in 2 minutes).
- **Domain Mismatch:** PaySim reflects African agent-assisted cash-in/cash-out models rather than instant peer-to-peer (P2P) or merchant (P2M) mobile QR payments.

### ULB Credit Card Limitations
- **PCA Anonymization:** Columns `V1` to `V28` are numerical principal components. They hide real-world semantic meaning (merchant category, device, recipient).
- **Missing Entity Identifiers:** ULB provides zero user IDs or recipient accounts, making sliding-window behavioral state tracking mathematically impossible.

### Justification for UPI Micro-Transaction Stream
- Preserves standard banking constraints while modeling rural user behaviors (e.g., Kirana store routine payments vs. rapid bot-driven OTP drain attacks).
- Implements exact ISO-8601 UTC timestamps, distinct UUID user entities, and Virtual Payment Address (VPA) targets required for sub-50ms behavioral scoring.

---

## 6. Architectural Transition to Phase 3
Based on the Phase 2 findings, **Phase 3 (Data Cleaning and Feature Engineering)** must implement:
1. **Sliding-Window Feature Vector Generator:**
   - 5-minute transaction count ($N_{5m}$)
   - 1-hour transaction count ($N_{1h}$)
   - 24-hour transaction count ($N_{24h}$)
2. **Inter-Arrival Time Delta:** $\Delta t = t_i - t_{i-1}$ (in seconds).
3. **Recipient Shannon Entropy:** Detecting rapid distribution across mule accounts.
4. **Amount Deviation Ratio:** $\frac{\text{amount}_i}{\mu_{\text{user}}}$.
5. **Leakage Prevention:** Strict backward-looking historical calculations without looking into future time steps.

