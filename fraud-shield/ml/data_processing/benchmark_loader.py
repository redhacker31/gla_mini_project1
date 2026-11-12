"""Benchmark Dataset Loader and Schema Handler for Fraud Shield.

Handles PaySim (Lopez-Rojas et al.), ULB Credit Card (Dal Pozzolo et al.),
and Indian UPI Micro-Transaction datasets.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os
import numpy as np
import pandas as pd


@dataclass
class DatasetMetadata:
    """Metadata describing a dataset schema and properties."""
    name: str
    target_column: str
    amount_column: str
    time_column: Optional[str]
    user_id_column: Optional[str]
    recipient_column: Optional[str]
    description: str


# Dataset definitions following published literature
PAYSIM_METADATA = DatasetMetadata(
    name="PaySim Mobile Money",
    target_column="isFraud",
    amount_column="amount",
    time_column="step",  # 1 step = 1 hour
    user_id_column="nameOrig",
    recipient_column="nameDest",
    description=(
        "Simulated mobile money transfers based on aggregated African financial logs. "
        "Contains 6.36M transactions with ~0.13% fraud rate."
    ),
)

ULB_METADATA = DatasetMetadata(
    name="ULB Credit Card",
    target_column="Class",
    amount_column="Amount",
    time_column="Time",  # Seconds elapsed from first transaction
    user_id_column=None,  # Anonymized; no user IDs
    recipient_column=None,  # No recipient IDs
    description=(
        "European cardholders credit card transactions transformed via PCA (V1-V28). "
        "Contains 284k transactions with ~0.17% fraud rate."
    ),
)

UPI_MICRO_METADATA = DatasetMetadata(
    name="Indian UPI Micro-Transactions",
    target_column="is_fraud",
    amount_column="amount",
    time_column="timestamp",
    user_id_column="user_id",
    recipient_column="recipient_vpa",
    description=(
        "Indian digital wallet micro-transactions (< INR 1,000) with realistic "
        "velocity bursts, smurfing, and phishing attacks under <0.2% fraud imbalance."
    ),
)


class BenchmarkLoader:
    """Loads and standardizes fraud benchmark datasets."""

    def __init__(self, data_dir: str = "ml/datasets"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def load_or_generate_paysim_sample(self, n_samples: int = 10000, random_state: int = 42) -> pd.DataFrame:
        """Load PaySim CSV if available, or generate a statistically faithful sample."""
        paysim_path = os.path.join(self.data_dir, "paysim_sample.csv")
        if os.path.exists(paysim_path):
            return pd.read_csv(paysim_path)

        rng = np.random.default_rng(random_state)
        fraud_count = max(int(n_samples * 0.0015), 15)  # ~0.15% fraud
        legit_count = n_samples - fraud_count

        # Types observed in PaySim: PAYMENT, TRANSFER, CASH_OUT, CASH_IN, DEBIT
        # (PaySim fraud only occurs in TRANSFER and CASH_OUT)
        legit_types = rng.choice(["PAYMENT", "TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"], size=legit_count, p=[0.35, 0.20, 0.25, 0.18, 0.02])
        fraud_types = rng.choice(["TRANSFER", "CASH_OUT"], size=fraud_count, p=[0.5, 0.5])

        types = np.concatenate([legit_types, fraud_types])
        steps = rng.integers(1, 744, size=n_samples)  # 30 days of hourly steps

        # Legitimate amounts log-normally distributed
        legit_amounts = np.round(rng.lognormal(mean=8.5, sigma=1.2, size=legit_count), 2)
        # Fraud amounts in PaySim often correspond to account emptying
        fraud_amounts = np.round(rng.lognormal(mean=11.0, sigma=0.8, size=fraud_count), 2)
        amounts = np.concatenate([legit_amounts, fraud_amounts])

        orig_ids = [f"C{rng.integers(1000000, 9999999)}" for _ in range(n_samples)]
        dest_ids = [f"M{rng.integers(1000000, 9999999)}" if t == "PAYMENT" else f"C{rng.integers(1000000, 9999999)}" for t in types]

        old_bal_orig = np.round(rng.exponential(scale=50000, size=n_samples), 2)
        new_bal_orig = np.maximum(0, old_bal_orig - amounts)
        old_bal_dest = np.round(rng.exponential(scale=30000, size=n_samples), 2)
        new_bal_dest = old_bal_dest + amounts

        is_fraud = np.zeros(n_samples, dtype=int)
        is_fraud[legit_count:] = 1
        is_flagged = np.where((is_fraud == 1) & (amounts > 200000), 1, 0)

        df = pd.DataFrame({
            "step": steps,
            "type": types,
            "amount": amounts,
            "nameOrig": orig_ids,
            "oldbalanceOrg": old_bal_orig,
            "newbalanceOrig": new_bal_orig,
            "nameDest": dest_ids,
            "oldbalanceDest": old_bal_dest,
            "newbalanceDest": new_bal_dest,
            "isFraud": is_fraud,
            "isFlaggedFraud": is_flagged,
        })

        # Shuffle
        df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
        df.to_csv(paysim_path, index=False)
        return df

    def load_or_generate_ulb_sample(self, n_samples: int = 10000, random_state: int = 42) -> pd.DataFrame:
        """Load ULB Credit Card CSV if available, or generate a statistically faithful PCA sample."""
        ulb_path = os.path.join(self.data_dir, "ulb_sample.csv")
        if os.path.exists(ulb_path):
            return pd.read_csv(ulb_path)

        rng = np.random.default_rng(random_state)
        fraud_count = max(int(n_samples * 0.0017), 17)  # ~0.17% fraud
        legit_count = n_samples - fraud_count

        times = np.sort(rng.uniform(0, 172800, size=n_samples))  # 48 hours in seconds

        # Generate 28 PCA components (V1-V28)
        # Fraud cases exhibit shifts in V1, V2, V3, V4, V10, V11, V12, V14, V17
        legit_v = rng.standard_normal(size=(legit_count, 28))
        fraud_v = rng.standard_normal(size=(fraud_count, 28))
        # Known signature anomalies in ULB
        fraud_v[:, 0] -= 2.5   # V1 shifted negative
        fraud_v[:, 1] += 2.0   # V2 shifted positive
        fraud_v[:, 3] += 3.0   # V4 shifted positive
        fraud_v[:, 9] -= 3.5   # V10 shifted negative
        fraud_v[:, 13] -= 4.0  # V14 shifted negative

        v_matrix = np.vstack([legit_v, fraud_v])

        legit_amounts = np.round(rng.lognormal(mean=3.0, sigma=1.3, size=legit_count), 2)
        fraud_amounts = np.round(rng.lognormal(mean=3.8, sigma=1.5, size=fraud_count), 2)
        amounts = np.concatenate([legit_amounts, fraud_amounts])

        classes = np.zeros(n_samples, dtype=int)
        classes[legit_count:] = 1

        data = {"Time": times}
        for i in range(28):
            data[f"V{i+1}"] = np.round(v_matrix[:, i], 6)
        data["Amount"] = amounts
        data["Class"] = classes

        df = pd.DataFrame(data).sample(frac=1.0, random_state=random_state).reset_index(drop=True)
        df.to_csv(ulb_path, index=False)
        return df
