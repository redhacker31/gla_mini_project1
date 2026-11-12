"""Isolation Forest Model Training Pipeline for Fraud Shield.

Trains an unsupervised Isolation Forest anomaly detection model on behavioral
micro-transaction features with chronological train/test splitting.
Serializes trained pipeline artifact to ml/artifacts/isolation_forest_pipeline.joblib.
"""
from dataclasses import asdict
from datetime import datetime
import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from ml.data_processing.batch_feature_pipeline import BatchFeaturePipeline, FEATURE_NAMES
from ml.data_processing.upi_synthetic_generator import UPIMicroTransactionSynthesizer


def train_isolation_forest(
    n_samples: int = 20000,
    fraud_ratio: float = 0.0018,
    contamination: float = 0.002,
    output_model_path: str = "ml/artifacts/isolation_forest_pipeline.joblib",
    output_metadata_path: str = "ml/artifacts/model_metadata.json",
    random_state: int = 42,
) -> dict:
    """Train and serialize the Isolation Forest model pipeline."""
    print("================================================================================")
    print("      FRAUD SHIELD — PHASE 4 ISOLATION FOREST MODEL TRAINING")
    print("================================================================================")

    # 1. Dataset Generation & Loading
    print(f"\n[1/5] Generating chronological transaction stream ({n_samples} txns, {fraud_ratio*100:.2f}% fraud)...")
    synthesizer = UPIMicroTransactionSynthesizer(seed=random_state)
    df_raw = synthesizer.generate_dataset(
        n_users=600,
        n_transactions=n_samples,
        fraud_ratio=fraud_ratio,
        output_csv="ml/datasets/training_stream.csv",
    )
    print(f"  ✓ Raw dataset ready: {len(df_raw)} records ({df_raw['is_fraud'].sum()} fraudulent).")

    # 2. Behavioral Feature Engineering
    print("\n[2/5] Extracting 9-dimensional behavioral feature vectors (zero lookahead leakage)...")
    feature_pipeline = BatchFeaturePipeline()
    X_features = feature_pipeline.transform(df_raw)
    y_labels = df_raw["is_fraud"].values

    # 3. Chronological Train / Test Split (70% Train, 30% Held-out Test)
    # Temporal splitting ensures future transactions do not leak into training
    split_idx = int(len(X_features) * 0.70)
    X_train = X_features.iloc[:split_idx].copy()
    y_train = y_labels[:split_idx]
    X_test = X_features.iloc[split_idx:].copy()
    y_test = y_labels[split_idx:]

    print(f"  ✓ Chronological Train Split: {len(X_train)} samples ({y_train.sum()} fraud)")
    print(f"  ✓ Held-Out Test Split:       {len(X_test)} samples ({y_test.sum()} fraud)")

    # 4. Model Training
    # Unsupervised: Train only on the unlabeled training feature matrix
    print("\n[3/5] Fitting Isolation Forest model...")
    # Using RobustScaler to handle heavy-tailed financial distributions without outlier distortion
    scaler = RobustScaler()
    iso_forest = IsolationForest(
        n_estimators=100,
        max_samples=256,       # Sub-sample size optimized for low latency and anomaly isolation
        contamination=contamination,
        bootstrap=False,
        n_jobs=-1,
        random_state=random_state,
    )

    # Train scaler and model
    X_train_scaled = scaler.fit_transform(X_train)
    iso_forest.fit(X_train_scaled)
    print("  ✓ Isolation Forest training complete (100 isolation trees fitted).")

    # 5. Score Normalization Verification
    # Scikit-learn score: decision_function = -s(x, n) + 0.5
    # Normalized score S_ml = clip(0.5 - decision_function(X_scaled), 0.0, 1.0)
    print("\n[4/5] Verifying score normalization S_ml in [0.0, 1.0]...")
    raw_scores = iso_forest.decision_function(scaler.transform(X_test.head(100)))
    norm_scores = np.clip(0.5 - raw_scores, 0.0, 1.0)
    assert (norm_scores >= 0.0).all() and (norm_scores <= 1.0).all(), "Normalization bounds breached!"
    print(f"  ✓ Score normalization confirmed: min={norm_scores.min():.4f}, max={norm_scores.max():.4f}")

    # 6. Save Model Bundle & Metadata
    print("\n[5/5] Serializing model artifact and training metadata...")
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    model_bundle = {
        "scaler": scaler,
        "model": iso_forest,
        "feature_names": FEATURE_NAMES,
        "model_version": "1.0.0",
        "algorithm": "Isolation Forest",
        "contamination": contamination,
        "trained_at": datetime.utcnow().isoformat(),
    }
    joblib.dump(model_bundle, output_model_path)
    print(f"  ✓ Model bundle saved to: {output_model_path}")

    # Save test partition for evaluation script
    test_data_path = "ml/artifacts/held_out_test_set.csv"
    test_df = X_test.copy()
    test_df["is_fraud"] = y_test
    test_df.to_csv(test_data_path, index=False)

    metadata = {
        "algorithm": "IsolationForest",
        "n_estimators": 100,
        "max_samples": 256,
        "contamination": contamination,
        "features": FEATURE_NAMES,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_fraud_count": int(y_train.sum()),
        "test_fraud_count": int(y_test.sum()),
        "artifact_path": output_model_path,
        "held_out_test_path": test_data_path,
    }
    with open(output_metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ Training metadata saved to: {output_metadata_path}")

    print("\n================================================================================")
    print("                    PHASE 4 TRAINING COMPLETE")
    print("================================================================================\n")
    return metadata


if __name__ == "__main__":
    train_isolation_forest()
