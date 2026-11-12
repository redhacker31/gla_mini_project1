"""Model Evaluation and Latency Benchmarking Harness for Fraud Shield.

Evaluates the trained Isolation Forest on held-out test data.
Measures Precision, Recall, PR-AUC, ROC-AUC, Recall @ 1% FPR,
and single-sample p95 inference latency.
"""
import json
import os
import time
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from ml.data_processing.batch_feature_pipeline import FEATURE_NAMES


def evaluate_model(
    model_path: str = "ml/artifacts/isolation_forest_pipeline.joblib",
    test_data_path: str = "ml/artifacts/held_out_test_set.csv",
    output_dir: str = "ml/artifacts",
) -> dict:
    """Evaluate Isolation Forest model on held-out test partition."""
    print("================================================================================")
    print("      FRAUD SHIELD — PHASE 4 MODEL EVALUATION & LATENCY BENCHMARK")
    print("================================================================================")

    # 1. Load Artifacts
    print(f"\n[1/4] Loading model bundle and held-out test dataset...")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}. Run train_isolation_forest.py first.")
    bundle = joblib.load(model_path)
    scaler = bundle["scaler"]
    model = bundle["model"]
    feature_names = bundle["feature_names"]

    df_test = pd.read_csv(test_data_path)
    X_test = df_test[feature_names].values
    y_test = df_test["is_fraud"].values
    total_test = len(y_test)
    fraud_test = int(np.sum(y_test))
    legit_test = total_test - fraud_test
    print(f"  ✓ Loaded test set: {total_test} samples ({fraud_test} fraud, {legit_test} legitimate).")

    # 2. Compute Normalized Anomaly Scores S_ml in [0, 1]
    print("\n[2/4] Scoring test set and computing normalized anomaly scores...")
    X_test_df = pd.DataFrame(X_test, columns=feature_names)
    X_test_scaled = scaler.transform(X_test_df)
    raw_decision = model.decision_function(X_test_scaled)
    # Normalized score: Higher means more anomalous (closer to 1.0)
    scores = np.clip(0.5 - raw_decision, 0.0, 1.0)

    # 3. Compute Metrics
    print("\n[3/4] Computing rigorous classification & ranking metrics...")
    roc_auc = float(roc_auc_score(y_test, scores))
    precisions, recalls, pr_thresholds = precision_recall_curve(y_test, scores)
    pr_auc = float(auc(recalls, precisions))

    # Recall at FPR <= 1.0% (Operational banking requirement)
    fpr, tpr, roc_thresholds = roc_curve(y_test, scores)
    valid_fpr_indices = np.where(fpr <= 0.01)[0]
    if len(valid_fpr_indices) > 0:
        recall_at_1pct_fpr = float(tpr[valid_fpr_indices[-1]])
        threshold_at_1pct_fpr = float(roc_thresholds[valid_fpr_indices[-1]])
    else:
        recall_at_1pct_fpr = 0.0
        threshold_at_1pct_fpr = 0.5

    # Binary evaluation at optimal F1 threshold
    f1_scores = 2 * (precisions * recalls) / np.maximum(precisions + recalls, 1e-8)
    best_idx = np.argmax(f1_scores)
    best_threshold = float(pr_thresholds[best_idx]) if best_idx < len(pr_thresholds) else 0.5
    y_pred_best = (scores >= best_threshold).astype(int)

    precision_at_best = float(precision_score(y_test, y_pred_best, zero_division=0))
    recall_at_best = float(recall_score(y_test, y_pred_best, zero_division=0))
    max_f1 = float(f1_score(y_test, y_pred_best, zero_division=0))

    # 4. Measure Single-Sample Inference Latency
    print("\n[4/4] Profiling single-sample inference latency (1,000 runs)...")
    latencies = []
    # Test random individual sample as DataFrame with proper feature names to avoid warnings
    sample_df = pd.DataFrame(X_test[0:1], columns=feature_names)
    for _ in range(1000):
        t0 = time.perf_counter()
        _ = np.clip(0.5 - model.decision_function(scaler.transform(sample_df)), 0.0, 1.0)
        latencies.append((time.perf_counter() - t0) * 1000.0)  # ms

    p50_latency = float(np.percentile(latencies, 50))
    p95_latency = float(np.percentile(latencies, 95))
    p99_latency = float(np.percentile(latencies, 99))
    mean_latency = float(np.mean(latencies))

    # Print Evaluation Table
    print("\n--------------------------------------------------------------------------------")
    print(f"{'METRIC':<36} | {'MEASURED VALUE':<18} | {'TARGET / REQUIREMENT'}")
    print("--------------------------------------------------------------------------------")
    print(f"{'PR-AUC (Precision-Recall Area)':<36} | {pr_auc:<18.4f} | >= 0.75 Target")
    print(f"{'ROC-AUC (Receiver Operating Area)':<36} | {roc_auc:<18.4f} | Standard Diagnostic")
    print(f"{'Recall @ 1% FPR':<36} | {recall_at_1pct_fpr*100:<17.2f}% | >= 75% Target")
    print(f"{'Optimal F1-Score':<36} | {max_f1:<18.4f} | Optimal Harmonic Mean")
    print(f"{'Precision @ Best Threshold':<36} | {precision_at_best*100:<17.2f}% | (Threshold: {best_threshold:.3f})")
    print(f"{'Recall @ Best Threshold':<36} | {recall_at_best*100:<17.2f}% | True Positive Rate")
    print("--------------------------------------------------------------------------------")
    print(f"{'p50 Inference Latency':<36} | {p50_latency:<18.3f} ms | Typical Latency")
    print(f"{'p95 Inference Latency':<36} | {p95_latency:<18.3f} ms | <= 20.0 ms Target")
    print(f"{'p99 Inference Latency':<36} | {p99_latency:<18.3f} ms | SLA Boundary")
    print("--------------------------------------------------------------------------------")

    # 5. Generate Curves Figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    ax1.plot(recalls, precisions, color="#3b82f6", lw=2, label=f"Isolation Forest (PR-AUC = {pr_auc:.3f})")
    ax1.axhline(y=fraud_test/total_test, color="r", linestyle="--", label=f"No-Skill Baseline ({fraud_test/total_test*100:.2f}%)")
    ax1.set_title("Precision-Recall Curve (Extreme Imbalance)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Recall")
    ax1.set_ylabel("Precision")
    ax1.set_ylim([0.0, 1.05])
    ax1.legend(loc="upper right")

    ax2.plot(fpr, tpr, color="#10b981", lw=2, label=f"ROC Curve (AUC = {roc_auc:.3f})")
    ax2.plot([0, 1], [0, 1], color="navy", linestyle="--")
    ax2.axvline(x=0.01, color="red", linestyle=":", label=f"1% FPR Line (Recall={recall_at_1pct_fpr*100:.1f}%)")
    ax2.set_title("ROC Curve & 1% FPR Boundary", fontsize=12, fontweight="bold")
    ax2.set_xlabel("False Positive Rate (FPR)")
    ax2.set_ylabel("True Positive Rate (Recall)")
    ax2.legend(loc="lower right")

    plt.tight_layout()
    curve_plot_path = os.path.join(output_dir, "pr_roc_curve.png")
    plt.savefig(curve_plot_path, dpi=200)
    plt.close()
    print(f"\n  ✓ PR and ROC visual curves saved to: {curve_plot_path}")

    # 6. Save JSON Report
    report_dict = {
        "model_algorithm": "IsolationForest",
        "test_dataset": {
            "total_records": total_test,
            "fraud_records": fraud_test,
            "legit_records": legit_test,
            "fraud_ratio": float(fraud_test / total_test),
        },
        "metrics": {
            "pr_auc": round(pr_auc, 4),
            "roc_auc": round(roc_auc, 4),
            "recall_at_1pct_fpr": round(recall_at_1pct_fpr, 4),
            "threshold_at_1pct_fpr": round(threshold_at_1pct_fpr, 4),
            "max_f1": round(max_f1, 4),
            "optimal_threshold": round(best_threshold, 4),
            "precision_at_optimal": round(precision_at_best, 4),
            "recall_at_optimal": round(recall_at_best, 4),
        },
        "latency_ms": {
            "p50": round(p50_latency, 3),
            "p95": round(p95_latency, 3),
            "p99": round(p99_latency, 3),
            "mean": round(mean_latency, 3),
            "target_sla": "<= 20.0 ms",
            "sla_met": bool(p95_latency <= 20.0),
        },
    }
    report_json_path = os.path.join(output_dir, "model_evaluation_report.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    print(f"  ✓ Full metric report saved to: {report_json_path}")
    print("\n================================================================================")
    print("                    PHASE 4 EVALUATION COMPLETE")
    print("================================================================================\n")
    return report_dict


if __name__ == "__main__":
    evaluate_model()
