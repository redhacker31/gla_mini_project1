"""Indian UPI Micro-Transaction Synthesizer.

Engineered specifically for the 'Fraud Shield' project synopsis.
Simulates low-value digital transactions (< INR 1,000) in rural/semi-urban India,
emulating realistic benign commerce and targeted low-ticket velocity attacks.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import os
import uuid
import numpy as np
import pandas as pd


class UPIMicroTransactionSynthesizer:
    """Generates synthetic Indian UPI micro-transaction streams."""

    POPULAR_VPA_HANDLES = ["@upi", "@okhdfcbank", "@okaxis", "@oksbi", "@paytm", "@ybl", "@ibl"]
    CHANNELS = ["UPI_APP", "QR_SCAN", "COLLECT_REQUEST", "P2P_INTENT"]

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def _generate_vpa(self, name_prefix: str) -> str:
        handle = self.rng.choice(self.POPULAR_VPA_HANDLES)
        suffix = self.rng.integers(10, 999)
        return f"{name_prefix.lower()}{suffix}{handle}"

    def generate_dataset(
        self,
        n_users: int = 500,
        n_transactions: int = 15000,
        fraud_ratio: float = 0.0018,  # 0.18% (realistic <0.2% extreme class imbalance)
        output_csv: Optional[str] = "ml/datasets/upi_micro_transactions.csv"
    ) -> pd.DataFrame:
        """Generate a realistic UPI micro-transaction dataset with temporal coherence."""
        base_time = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)

        # 1. Generate user population
        users = [str(uuid.uuid4()) for _ in range(n_users)]
        # Assign typical daily spending profile per user
        user_profiles = {}
        for u in users:
            user_profiles[u] = {
                "base_amount_mean": float(self.rng.uniform(80.0, 350.0)),
                "base_amount_std": float(self.rng.uniform(15.0, 80.0)),
                "frequent_recipients": [self._generate_vpa(f"merchant_{i}") for i in range(self.rng.integers(2, 6))],
                "last_txn_time": base_time + timedelta(minutes=float(self.rng.integers(0, 300))),
            }

        target_fraud_txns = max(int(n_transactions * fraud_ratio), 25)
        target_legit_txns = n_transactions - target_fraud_txns

        records: List[Dict] = []

        # 2. Generate Benign Micro-Commerce (Routine Grocery, Tea Stalls, Kirana)
        for _ in range(target_legit_txns):
            user_id = self.rng.choice(users)
            profile = user_profiles[user_id]

            # Inter-arrival delta-t: legitimate transactions are hours or days apart
            delta_minutes = float(self.rng.exponential(scale=360.0) + 15.0)  # Average 6 hours apart
            txn_time = profile["last_txn_time"] + timedelta(minutes=delta_minutes)
            profile["last_txn_time"] = txn_time

            # Normal micro-amounts: usually under INR 500 (tea, grocery, daily needs)
            amount = float(np.clip(
                self.rng.normal(profile["base_amount_mean"], profile["base_amount_std"]),
                a_min=10.0,
                a_max=950.0
            ))

            # 90% chance to pay a known recurring merchant (low recipient entropy)
            if self.rng.random() < 0.90:
                recipient = self.rng.choice(profile["frequent_recipients"])
            else:
                recipient = self._generate_vpa("new_vendor")

            channel = self.rng.choice(self.CHANNELS, p=[0.55, 0.35, 0.05, 0.05])

            records.append({
                "txn_id": str(uuid.uuid4()),
                "user_id": user_id,
                "amount": round(amount, 2),
                "timestamp": txn_time.isoformat(),
                "recipient_vpa": recipient,
                "channel": channel,
                "is_fraud": 0,
                "fraud_type": "NONE",
            })

        # 3. Inject Anomalous Attacks (< 0.2% fraud)
        # Type A: Velocity Burst (5-8 transactions within 3 minutes)
        # Type B: Smurfing / Micro-Draining (rapid small round transfers to diverse recipients)
        # Type C: Collect-Request Phishing (unusual incoming payment pull)
        fraud_generated = 0
        attack_types = ["VELOCITY_BURST", "SMURFING", "COLLECT_PHISHING"]

        while fraud_generated < target_fraud_txns:
            attack_type = self.rng.choice(attack_types, p=[0.50, 0.35, 0.15])
            victim_user_id = self.rng.choice(users)
            victim_profile = user_profiles[victim_user_id]
            attack_start = victim_profile["last_txn_time"] + timedelta(hours=float(self.rng.integers(1, 48)))

            if attack_type == "VELOCITY_BURST":
                burst_count = min(self.rng.integers(5, 9), target_fraud_txns - fraud_generated)
                curr_t = attack_start
                for _ in range(burst_count):
                    curr_t += timedelta(seconds=float(self.rng.uniform(10.0, 45.0)))  # High frequency!
                    amount = float(self.rng.uniform(250.0, 499.0))  # Just below 500 alarm limit
                    recipient = self._generate_vpa("attacker_mule")
                    records.append({
                        "txn_id": str(uuid.uuid4()),
                        "user_id": victim_user_id,
                        "amount": round(amount, 2),
                        "timestamp": curr_t.isoformat(),
                        "recipient_vpa": recipient,
                        "channel": "UPI_APP",
                        "is_fraud": 1,
                        "fraud_type": "VELOCITY_BURST",
                    })
                    fraud_generated += 1

            elif attack_type == "SMURFING":
                smurf_count = min(self.rng.integers(4, 7), target_fraud_txns - fraud_generated)
                curr_t = attack_start
                for _ in range(smurf_count):
                    curr_t += timedelta(seconds=float(self.rng.uniform(30.0, 90.0)))
                    # Fixed round-tripping micro amounts
                    amount = float(self.rng.choice([199.0, 299.0, 399.0, 480.0]))
                    recipient = self._generate_vpa("smurf_wallet")
                    records.append({
                        "txn_id": str(uuid.uuid4()),
                        "user_id": victim_user_id,
                        "amount": round(amount, 2),
                        "timestamp": curr_t.isoformat(),
                        "recipient_vpa": recipient,
                        "channel": "P2P_INTENT",
                        "is_fraud": 1,
                        "fraud_type": "SMURFING",
                    })
                    fraud_generated += 1

            else:  # COLLECT_PHISHING
                curr_t = attack_start + timedelta(seconds=15)
                records.append({
                    "txn_id": str(uuid.uuid4()),
                    "user_id": victim_user_id,
                    "amount": 999.0,  # Maximizing micro-transaction limit
                    "timestamp": curr_t.isoformat(),
                    "recipient_vpa": self._generate_vpa("phishing_collect"),
                    "channel": "COLLECT_REQUEST",
                    "is_fraud": 1,
                    "fraud_type": "COLLECT_PHISHING",
                })
                fraud_generated += 1

        df = pd.DataFrame(records)
        # Sort chronologically by timestamp
        df["dt"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="dt").drop(columns=["dt"]).reset_index(drop=True)

        if output_csv:
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            df.to_csv(output_csv, index=False)

        return df

