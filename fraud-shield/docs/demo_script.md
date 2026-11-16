# Fraud Shield: Interactive Evaluator Demonstration & Viva Script
## Capstone Project Technical Walkthrough

---

**Project Title:** Fraud Shield — Real-Time Anomaly Detection for Digital Micro-Transactions  
**Academic Context:** B.Tech AIML Capstone Project, GLA University  
**Team Name & ID:** Quantumm Coders (Team ID: 40)  
**Target Audience:** Faculty Evaluation Committee, External Examiners, and Project Viva Panel  
**Estimated Demonstration Duration:** 10–12 Minutes

---

## 1. Pre-Demonstration Setup Checklist

Before presenting to the viva panel, ensure the application stack is running:

### Option A: Cloud-Native Docker Deployment (Recommended)
```bash
# From repository root or fraud-shield directory:
docker compose up --build -d

# Verify both containers are healthy
docker compose ps
```

### Option B: Local Development Execution
```bash
# Terminal 1: Backend FastAPI ASGI Service
cd fraud-shield/backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend React Dashboard
cd fraud-shield/frontend
npm run dev
```

### Live URLs for Presentation:
- **Analyst Telemetry Dashboard:** [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Healthcheck & ML Telemetry Probe:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 2. Minute-by-Minute Demonstration Walkthrough

```
+-----------------------------------------------------------------------------------------+
| Timeline | Section / Scenario                       | Target System Component            |
+-----------------------------------------------------------------------------------------+
| 00:00    | 1. System Introduction & Problem Context | Slide / Concept Introduction       |
| 01:30    | 2. Scenario 1: Benign Micro-Commerce     | Evaluator Tab / Transaction Feed   |
| 03:00    | 3. Scenario 2: Velocity Burst & Step-Up  | Step-Up OTP Challenge Modal        |
| 05:00    | 4. Scenario 3: Blacklisted Mule Syndicate| Transaction Ingestion Gateway      |
| 06:30    | 5. Scenario 4: Explainability Studio     | SHAP Marginal Attribution Studio   |
| 08:00    | 6. Scenario 5: Cryptographic Audit Ledger| SHA-256 Tamper-Evident Ring        |
| 09:30    | 7. Scenario 6: Adversarial Attack Stream | Real-Time Transaction Generator    |
| 10:45    | 8. Scenario 7: Sub-50ms Benchmarks & SLA | Performance Profiling Modal        |
+-----------------------------------------------------------------------------------------+
```

---

### Step 1: System Introduction & Architectural Overview (00:00 – 01:30)
- **Presenter Action:** Open the Dashboard at `http://localhost:5173`. Point out the header ribbon showing **Health: Healthy**, **Model: Isolation Forest (PR-AUC 0.8119)**, and **Database: SQLite WAL Mode**.
- **Presenter Talking Points:**
  > *"Respected evaluators, over 80% of India's daily UPI volume consists of micro-transactions under INR 1,000. While major banks secure large transfers, vulnerable rural users face micro-fraud attacks—like rapid draining bursts and phishing—that fall beneath static bank alert thresholds. Fraud Shield solves this by combining unsupervised Isolation Forest anomaly detection with deterministic rules and adaptive Step-Up OTP challenges, all operating within a strict sub-50ms edge budget."*

---

### Step 2: Scenario 1 — Benign Micro-Commerce Auto-Approval (01:30 – 03:00)
- **Objective:** Demonstrate that routine, legitimate payments are auto-approved in under 15ms with **zero user friction**.
- **Presenter Action:** 
  1. Scroll down to the **Manual Transaction Evaluator** on the dashboard.
  2. Enter or select the **Routine Grocery** preset:
     - **User ID:** `user_ramesh_01`
     - **Amount:** `120.00` INR
     - **Recipient:** `grocery_store@upi`
     - **Category:** `grocery`
  3. Click **"Evaluate Transaction"**.
- **Observed Result:**
  - Decision: **`ALLOW` (LOW RISK)**
  - Risk Score: **`~0.12 - 0.22`** ($S(x) < 0.45$)
  - Evaluation Latency: **`~10 - 15ms`** (green badge).
  - An entry immediately appears in the **Live Transaction Feed**.
- **Presenter Talking Points:**
  > *"Notice that Ramesh's INR 120 grocery purchase was evaluated in approximately 12ms. Because his velocity is zero in the last 5 minutes and the amount is routine, the Isolation Forest path length is deep and no security rules are tripped. The transaction is instantly approved with zero user friction."*

---

### Step 3: Scenario 2 — Velocity Burst Attack & Step-Up OTP Challenge (03:00 – 05:00)
- **Objective:** Demonstrate how sudden velocity bursts trigger a **Medium Risk** Step-Up OTP challenge to prevent unauthorized account draining.
- **Presenter Action:**
  1. In the **Manual Transaction Evaluator**, enter:
     - **User ID:** `user_priya_02`
     - **Amount:** `450.00` INR
     - **Recipient:** `unregistered_merchant_99@upi`
     - **Category:** `electronics`
  2. Submit the transaction 3 times in rapid succession (simulating an attacker rapidly draining funds).
- **Observed Result:**
  - On the 3rd or 4th submission, the Decision shifts to **`CHALLENGE` (MEDIUM RISK)**.
  - Risk Score rises into the **`[0.45, 0.80)`** bracket.
  - A modal automatically appears: **"Step-Up Authentication Required"**.
  - The modal displays the challenged Transaction ID, the masked phone number (`+91 ******1234`), a countdown timer (180s TTL), and a **Simulated SMS Notification Banner** displaying the CSPRNG 6-digit OTP (e.g., `849201`).
  3. Enter the displayed 6-digit OTP and click **"Verify OTP"**.
  - Modal transitions to **"Verification Successful! Transaction Approved"**.
  - Transaction Feed updates the status from `CHALLENGE_PENDING` to `CHALLENGE_VERIFIED`.
- **Presenter Talking Points:**
  > *"Here, our behavioral feature pipeline detected multiple rapid transfers within a 5-minute window, causing the inter-arrival delta-t to collapse to just a few seconds. The Isolation Forest flagged an anomaly and Rule 1 triggered. Rather than blindly blocking Priya, Fraud Shield adaptively challenged the transaction with a 6-digit CSPRNG OTP. Once verified, the payment proceeded seamlessly."*

---

### Step 4: Scenario 3 — Blacklisted Syndicate Mule Account (05:00 – 06:30)
- **Objective:** Demonstrate immediate high-risk blocking when funds are directed to known syndicate mule accounts.
- **Presenter Action:**
  1. In the **Manual Transaction Evaluator**, enter:
     - **User ID:** `user_vikram_03`
     - **Amount:** `900.00` INR
     - **Recipient:** `mule_syndicate_01@upi` (pre-configured in the blacklist registry)
     - **Category:** `transfer`
  2. Click **"Evaluate Transaction"**.
- **Observed Result:**
  - Decision: **`BLOCK` (HIGH RISK)** in bright red.
  - Risk Score: **`~0.98 - 0.99`** ($S(x) \ge 0.80$).
  - Rule Audit Matrix highlights **R8: Blacklisted Syndicate Mule Account** triggered with critical penalty $+5.00$.
  - Persistent alert dispatched in the UI.
- **Presenter Talking Points:**
  > *"When an attempt is made to transfer funds to a known syndicate mule VPA, deterministic Rule 8 activates with a critical logit weight of 5.0. This immediately overrides borderline ML scores and forces the Composite Risk Score to 0.99, freezing the transaction instantly without burdening the user with an OTP."*

---

### Step 5: Scenario 4 — Explainability Studio & "What-If" Sensitivity Analysis (06:30 – 08:00)
- **Objective:** Prove that Fraud Shield is fully transparent and explainable, not an uninterpretable "black box".
- **Presenter Action:**
  1. Click the **"Explainability Studio"** button in the Navbar.
  2. Point out the interactive controls:
     - **Amount Slider:** Drag amount from 100 to 950 INR.
     - **5-Minute Count Slider:** Drag from 0 to 6 transactions.
     - **Delta-t Slider:** Drag from 3,600s down to 5s.
  3. Observe the live updating **SHAP Waterfall Attribution Bar Chart**:
     - Marginal feature attribution deltas ($\Delta S_i = S_{\text{ml}}(\mathbf{x}) - S_{\text{ml}}(\mathbf{x}_{-i})$) dynamically update in real time.
     - Green bars indicate benign influence; red bars indicate anomalous risk contributions.
  4. Point out the **Calibrated Sigmoid Fusion Inspector**:
     - Displays the exact mathematical formula: $z = z_0 + z_{\text{ml}} + z_{\text{rules}}$ and $S(\mathbf{x}) = \frac{1}{1 + e^{-z}}$.
- **Presenter Talking Points:**
  > *"Financial regulators and bank compliance officers require explainable AI. Fraud Shield provides full transparency through our sub-millisecond marginal attribution engine. By isolating the delta S_i of each feature against its baseline median, analysts can see exactly why an evaluation was challenged or blocked."*

---

### Step 6: Scenario 5 — Cryptographic Audit Ledger & Tamper Verification (08:00 – 09:30)
- **Objective:** Demonstrate DPDP Act 2023 compliance, user pseudonymization, and cryptographic non-repudiation.
- **Presenter Action:**
  1. In the Navbar, click **"Audit Ledger"**.
  2. The **Cryptographic Audit Ledger Modal** opens, displaying recent chained records.
  3. Point out key ledger attributes:
     - **Block Index & Timestamp**
     - **Salted SHA-256 User Pseudonym:** e.g., `a7f9c2...` (raw phone number / VPA is never stored).
     - **Previous Block Hash ($H_{k-1}$)** and **Current Block Hash ($H_k$)**.
  4. Click **"Verify Hash Ring Integrity"**.
  5. The system performs an end-to-end traversal from genesis ($H_0 = \text{"0"}^{64}$) to the latest tip.
  - Verification badge displays: **"Ledger Provenance Verified: 100% Tamper-Free"**.
- **Presenter Talking Points:**
  > *"Under the Digital Personal Data Protection Act 2023, payment systems must enforce data minimization and pseudonymization. Fraud Shield stores only salted SHA-256 user hashes. Furthermore, every decision is cryptographically chained to its predecessor using SHA-256. If a malicious insider attempts to modify any past transaction amount or decision, the entire downstream hash chain breaks, providing forensic proof of tampering."*

---

### Step 7: Scenario 6 — Multi-Threaded Adversarial Attack Simulator (09:30 – 10:45)
- **Objective:** Showcase the system handling high-throughput adversarial attack streams in real time.
- **Presenter Action:**
  1. Navigate to the **Adversarial Simulation Control Panel**.
  2. Select the **Adversarial Attack Suite (50 txns)** preset (containing interleaved velocity bursts, micro-draining smurfing, and phishing attacks).
  3. Click **"Run Simulation Burst"**.
  4. Watch the UI:
     - KPI cards (**Total Evaluated**, **Allowed**, **Challenged**, **Blocked**) increment dynamically.
     - The **Risk Distribution Doughnut Chart** updates smoothly.
     - The **Live Transaction Feed** streams processed transactions in real time with individual latency tags ($<15\text{ms}$).
- **Presenter Talking Points:**
  > *"Here, our adversarial generator dispatches a multi-vector attack stream. Notice how the system separates routine transactions into Low Risk while systematically isolating smurfing and velocity attacks into Challenge or Block states without dropping throughput or exceeding latency budgets."*

---

### Step 8: Scenario 7 — Sub-50ms Benchmarking & SLA Compliance (10:45 – 12:00)
- **Objective:** Conclusively demonstrate sub-50ms latency compliance across all pipeline components.
- **Presenter Action:**
  1. In the Navbar, click **"Performance Benchmarks"**.
  2. The **System Performance & Latency Benchmark Modal** opens.
  3. Point out the subcomponent latency cards:
     - **Feature Extraction:** $0.08\text{ ms}$ (Budget: $10.0\text{ ms}$)
     - **Isolation Forest ML:** $10.07\text{ ms}$ (Budget: $20.0\text{ ms}$)
     - **Deterministic Rules:** $0.11\text{ ms}$ (Budget: $5.0\text{ ms}$)
     - **Persistence & Cryptographic Hash:** $8.99\text{ ms}$ (Budget: $15.0\text{ ms}$)
     - **Total End-to-End Latency:** **$12.15\text{ ms}$ Mean, $17.27\text{ ms}$ p95** (Budget: $\le 50.0\text{ ms}$).
  4. Highlight the **Concurrency Stress Test** metrics:
     - **53.7 Requests/sec**, **0.0% Error Rate**.
- **Presenter Talking Points:**
  > *"To conclude, Fraud Shield satisfies all technical and academic objectives. Our p95 end-to-end latency is 17.27ms, providing over 65% safety headroom under the 50ms edge budget. This proves that real-time AI/ML fraud detection can be deployed seamlessly at the edge on standard hardware."*

---

## 3. Anticipated Viva Panel Questions & Answers

### Q1: Why choose unsupervised Isolation Forest instead of supervised models like XGBoost or Random Forest?
**Answer:**  
In digital micro-payments, ground-truth fraud labels suffer from severe latency (victims report unauthorized transactions days later) and extreme class imbalance ($< 0.2\%$ fraud prevalence). Supervised models overfit to known historical patterns and fail when fraudsters invent new draining tactics. Isolation Forest is unsupervised; it requires no labels and detects anomalies purely based on their topological isolation in feature space via short decision tree paths. Furthermore, with `max_samples=256` and 100 trees, it executes in under 11ms on CPU without requiring expensive GPU infrastructure.

### Q2: How does Fraud Shield handle database lock contention under high-throughput concurrent transactions?
**Answer:**  
Under multi-threaded payment bursts, standard SQLite databases can suffer from write lock contention. Fraud Shield implements three levels of optimization:
1. **Write-Ahead Logging (WAL):** Enabled via `PRAGMA journal_mode=WAL`, allowing concurrent readers to read without blocking the single writer.
2. **Busy Timeout & Synchronous Normal:** Configured `PRAGMA busy_timeout=5000` to automatically queue transient locks for up to 5 seconds.
3. **SQLAlchemy Nested Savepoints:** Implemented `db.begin_nested()` around user creation to cleanly recover from concurrency race conditions without rolling back the outer transaction. Our benchmark verified 53.7 RPS with 0% errors across 10 concurrent threads.

### Q3: How do you prevent attackers from gaming the static rule thresholds?
**Answer:**  
In Fraud Shield, deterministic rules and ML scores do not act as isolated binary gates; they are blended through our **Calibrated Logistic Sigmoid Fusion** formula. An attacker who keeps velocity just under Rule 1's threshold (e.g., 4 transactions in 5 minutes instead of 5) still causes a high ML anomaly score in Isolation Forest due to abnormal feature combinations. The logit fusion smoothly combines these signals into a risk score that still lands in the Medium Risk challenge band.

### Q4: How is user privacy protected in compliance with the DPDP Act 2023?
**Answer:**  
Fraud Shield strictly adheres to Section 8 (Data Minimization) and Section 9 (Pseudonymization) of India's DPDP Act 2023. Raw phone numbers, bank account details, and government IDs are never persisted to disk. User identities are pseudonymized using a cryptographic salted hash (`HMAC-SHA256(salt, user_id)`). Only necessary behavioral vectors (timestamps, amounts, categories) are evaluated, and all records are immutably preserved in an append-only SHA-256 cryptographic audit ledger.

---
**Quantumm Coders (Team ID: 40)**  
Department of Computer Science & Engineering (AIML Program)  
GLA University, Mathura, Uttar Pradesh, India
