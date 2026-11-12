"""Exploratory Data Analysis (EDA) Runner.

Executes comprehensive comparative inspection across PaySim, ULB,
and Indian UPI Micro-Transaction datasets. Generates figures and summary tables.
"""
from dataclasses import asdict
import json
import os
import matplotlib
matplotlib.use("Agg")  # Headless backend for scripts
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from ml.data_processing.benchmark_loader import (
    BenchmarkLoader,
    PAYSIM_METADATA,
    ULB_METADATA,
    UPI_MICRO_METADATA,
)
from ml.data_processing.dataset_inspector import DatasetInspector
from ml.data_processing.upi_synthetic_generator import UPIMicroTransactionSynthesizer


def run_full_eda(output_dir: str = "ml/artifacts") -> dict:
    """Run full comparative EDA on PaySim, ULB, and UPI datasets."""
    os.makedirs(output_dir, exist_ok=True)
    print("================================================================================")
    print("           FRAUD SHIELD — PHASE 2 EXPLORATORY DATA ANALYSIS (EDA)")
    print("================================================================================")

    loader = BenchmarkLoader()
    upi_gen = UPIMicroTransactionSynthesizer(seed=42)

    # 1. Acquire / Load datasets
    print("\n[1/4] Loading and preparing benchmark datasets...")
    df_paysim = loader.load_or_generate_paysim_sample(n_samples=10000, random_state=42)
    print(f"  ✓ PaySim Sample Loaded: {df_paysim.shape[0]} rows, {df_paysim.shape[1]} columns")

    df_ulb = loader.load_or_generate_ulb_sample(n_samples=10000, random_state=42)
    print(f"  ✓ ULB Credit Card Sample Loaded: {df_ulb.shape[0]} rows, {df_ulb.shape[1]} columns")

    df_upi = upi_gen.generate_dataset(n_users=500, n_transactions=15000, fraud_ratio=0.0018)
    print(f"  ✓ Indian UPI Micro-Transaction Stream Generated: {df_upi.shape[0]} rows, {df_upi.shape[1]} columns")

    # 2. Inspect datasets
    print("\n[2/4] Executing structural & class imbalance audits...")
    paysim_inspector = DatasetInspector(PAYSIM_METADATA.name)
    paysim_report = paysim_inspector.inspect(
        df_paysim,
        target_col=PAYSIM_METADATA.target_column,
        amount_col=PAYSIM_METADATA.amount_column,
        time_col=PAYSIM_METADATA.time_column,
        user_col=PAYSIM_METADATA.user_id_column,
        recipient_col=PAYSIM_METADATA.recipient_column,
        limitations=[
            "Coarse 1-hour time step ('step') prevents sub-minute velocity tracking.",
            "Lacks UPI Virtual Payment Address (VPA) structure.",
            "Contains large cross-border business amounts unrepresentative of Indian rural micro-commerce.",
        ],
    )

    ulb_inspector = DatasetInspector(ULB_METADATA.name)
    ulb_report = ulb_inspector.inspect(
        df_ulb,
        target_col=ULB_METADATA.target_column,
        amount_col=ULB_METADATA.amount_column,
        time_col=ULB_METADATA.time_column,
        user_col=ULB_METADATA.user_id_column,
        recipient_col=ULB_METADATA.recipient_column,
        limitations=[
            "Features V1-V28 are PCA-anonymized; cannot infer user behavioral intent.",
            "No user or recipient IDs available; impossible to compute sliding-window velocity or recipient entropy.",
            "Static credit card transaction records rather than streaming mobile wallet micro-payments.",
        ],
    )

    upi_inspector = DatasetInspector(UPI_MICRO_METADATA.name)
    upi_report = upi_inspector.inspect(
        df_upi,
        target_col=UPI_MICRO_METADATA.target_column,
        amount_col=UPI_MICRO_METADATA.amount_column,
        time_col=UPI_MICRO_METADATA.time_column,
        user_col=UPI_MICRO_METADATA.user_id_column,
        recipient_col=UPI_MICRO_METADATA.recipient_column,
        limitations=[
            "Synthetically generated due to strict banking privacy regulations (RBI / DPDP Act).",
            "Models rural micro-transactions specifically (< INR 1,000); not generalized to corporate wire transfers.",
        ],
    )

    # 3. Print Comparison Tables
    print("\n--------------------------------------------------------------------------------")
    print(f"{'DATASET':<28} | {'RECORDS':<9} | {'FRAUD':<7} | {'FRAUD %':<9} | {'IMBALANCE RATIO'}")
    print("--------------------------------------------------------------------------------")
    for r in [paysim_report, ulb_report, upi_report]:
        imb = r.imbalance
        print(f"{r.dataset_name:<28} | {imb.total_records:<9} | {imb.fraud_records:<7} | {imb.fraud_percentage:<8}% | {imb.imbalance_ratio}")
    print("--------------------------------------------------------------------------------")

    print("\n--------------------------------------------------------------------------------")
    print(f"{'DATASET':<28} | {'LEGIT MEAN':<12} | {'LEGIT MEDIAN':<12} | {'FRAUD MEAN':<12} | {'FRAUD MEDIAN'}")
    print("--------------------------------------------------------------------------------")
    for r in [paysim_report, ulb_report, upi_report]:
        l_stat = r.legit_amount_stats
        f_stat = r.fraud_amount_stats
        print(f"{r.dataset_name:<28} | INR {l_stat.mean:<8.2f} | INR {l_stat.median:<8.2f} | INR {f_stat.mean:<8.2f} | INR {f_stat.median:.2f}")
    print("--------------------------------------------------------------------------------")

    # 4. Generate Visualization Figures
    print("\n[3/4] Generating academic visual charts...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Extreme Class Imbalance Comparison
    names = [r.dataset_name.split()[0] for r in [paysim_report, ulb_report, upi_report]]
    fraud_pcts = [r.imbalance.fraud_percentage for r in [paysim_report, ulb_report, upi_report]]
    bars = axes[0, 0].bar(names, fraud_pcts, color=["#3b82f6", "#6366f1", "#ef4444"], width=0.5)
    axes[0, 0].set_title("Extreme Class Imbalance (% Fraud < 0.2%)", fontsize=12, fontweight="bold")
    axes[0, 0].set_ylabel("Fraud Percentage (%)")
    axes[0, 0].set_ylim(0, 0.35)
    for bar in bars:
        yval = bar.get_height()
        axes[0, 0].text(bar.get_x() + bar.get_width()/2.0, yval + 0.01, f"{yval:.3f}%", ha="center", va="bottom", fontweight="bold")

    # Plot 2: UPI Micro-Transaction Amount Distribution by Class
    legit_upi_amts = df_upi.loc[df_upi["is_fraud"] == 0, "amount"]
    fraud_upi_amts = df_upi.loc[df_upi["is_fraud"] == 1, "amount"]
    axes[0, 1].hist(legit_upi_amts, bins=30, alpha=0.6, label="Legitimate (< INR 1,000)", color="#10b981", density=True)
    axes[0, 1].hist(fraud_upi_amts, bins=20, alpha=0.7, label="Fraud Attack Bursts", color="#ef4444", density=True)
    axes[0, 1].set_title("UPI Amount Density: Legitimate vs. Fraud", fontsize=12, fontweight="bold")
    axes[0, 1].set_xlabel("Amount (INR)")
    axes[0, 1].set_ylabel("Density")
    axes[0, 1].legend()

    # Plot 3: UPI Inter-Arrival Delta-T (Time Between Consecutive Transactions per User)
    df_upi_sorted = df_upi.sort_values(by=["user_id", "timestamp"]).copy()
    df_upi_sorted["t"] = pd.to_datetime(df_upi_sorted["timestamp"])
    df_upi_sorted["delta_sec"] = df_upi_sorted.groupby("user_id")["t"].diff().dt.total_seconds().fillna(3600)
    legit_delta = np.log10(np.clip(df_upi_sorted.loc[df_upi_sorted["is_fraud"] == 0, "delta_sec"], 1, 100000))
    fraud_delta = np.log10(np.clip(df_upi_sorted.loc[df_upi_sorted["is_fraud"] == 1, "delta_sec"], 1, 100000))
    axes[1, 0].boxplot([legit_delta, fraud_delta], tick_labels=["Legitimate", "Velocity Attack"], patch_artist=True)
    axes[1, 0].set_title("Inter-Arrival Time Log10(Δt in seconds)", fontsize=12, fontweight="bold")
    axes[1, 0].set_ylabel("Log10(Seconds Between Txns)")

    # Plot 4: Feature Availability Matrix
    feature_matrix = pd.DataFrame([
        [1, 0, 1, 1, 0],  # PaySim: Has Amt, No sub-minute time, Has User, Has Recipient, No Velocity
        [1, 1, 0, 0, 0],  # ULB: Has Amt, Has Time, No User, No Recipient, No Velocity
        [1, 1, 1, 1, 1],  # UPI Micro: All present
    ], index=["PaySim", "ULB Credit", "UPI Micro"], columns=["Amount", "Fine Time", "User ID", "Recipient VPA", "Rolling Velocity"])
    sns.heatmap(feature_matrix, annot=True, cbar=False, cmap="Blues", ax=axes[1, 1], linewidths=1)
    axes[1, 1].set_title("Feature Availability for Behavioral Modeling", fontsize=12, fontweight="bold")

    plt.tight_layout()
    plot_path = os.path.join(output_dir, "eda_comparison_overview.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"  ✓ High-resolution visualization saved to: {plot_path}")

    # 5. Serialize Summary Report
    print("\n[4/4] Writing EDA summary JSON report...")
    summary = {
        "paysim": asdict(paysim_report),
        "ulb": asdict(ulb_report),
        "upi_micro": asdict(upi_report),
    }
    json_path = os.path.join(output_dir, "eda_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ Statistical report saved to: {json_path}")
    print("\n================================================================================")
    print("                    PHASE 2 EDA EXECUTION COMPLETE")
    print("================================================================================\n")
    return summary


if __name__ == "__main__":
    run_full_eda()

