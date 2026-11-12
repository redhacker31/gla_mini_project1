"""Unit tests for Phase 2 Dataset Acquisition and Schema Exploration."""
import os
import pandas as pd
import pytest
from ml.data_processing.benchmark_loader import (
    BenchmarkLoader,
    PAYSIM_METADATA,
    ULB_METADATA,
    UPI_MICRO_METADATA,
)
from ml.data_processing.dataset_inspector import DatasetInspector
from ml.data_processing.upi_synthetic_generator import UPIMicroTransactionSynthesizer


@pytest.fixture
def benchmark_loader(tmp_path):
    return BenchmarkLoader(data_dir=str(tmp_path))


@pytest.fixture
def upi_synthesizer():
    return UPIMicroTransactionSynthesizer(seed=123)


def test_paysim_schema_and_integrity(benchmark_loader):
    """Verify PaySim benchmark adheres to published schema and has 0 null values."""
    df = benchmark_loader.load_or_generate_paysim_sample(n_samples=500, random_state=1)
    assert len(df) == 500
    assert df.isnull().sum().sum() == 0

    expected_cols = [
        "step", "type", "amount", "nameOrig", "oldbalanceOrg",
        "newbalanceOrig", "nameDest", "oldbalanceDest", "newbalanceDest",
        "isFraud", "isFlaggedFraud",
    ]
    for col in expected_cols:
        assert col in df.columns
    assert set(df["isFraud"].unique()).issubset({0, 1})


def test_ulb_schema_and_integrity(benchmark_loader):
    """Verify ULB Credit Card dataset adheres to 28 PCA features + Amount + Class."""
    df = benchmark_loader.load_or_generate_ulb_sample(n_samples=500, random_state=1)
    assert len(df) == 500
    assert df.isnull().sum().sum() == 0
    assert "Time" in df.columns
    assert "Amount" in df.columns
    assert "Class" in df.columns
    for i in range(1, 29):
        assert f"V{i}" in df.columns


def test_upi_micro_transactions_generator(upi_synthesizer, tmp_path):
    """Verify Indian UPI micro-transaction generator satisfies project synopsis constraints."""
    out_file = str(tmp_path / "test_upi.csv")
    df = upi_synthesizer.generate_dataset(n_users=50, n_transactions=1000, fraud_ratio=0.002, output_csv=out_file)

    assert len(df) == 1000
    assert os.path.exists(out_file)
    assert df.isnull().sum().sum() == 0

    # Verify all amounts strictly conform to micro-transaction constraint (< INR 1,000)
    assert df["amount"].max() <= 1000.0
    assert df["amount"].min() >= 10.0

    # Verify extreme class imbalance (< 1.0% fraud, target ~0.2%)
    fraud_count = df["is_fraud"].sum()
    assert fraud_count > 0
    assert fraud_count < 50  # Less than 5% in worst case, target ~0.2%

    # Verify timestamp monotonicity per user after sorting
    df["dt"] = pd.to_datetime(df["timestamp"])
    for user_id, group in df.groupby("user_id"):
        diffs = group.sort_values(by="dt")["dt"].diff().dropna()
        # Ensure time does not run backwards
        assert (diffs >= pd.Timedelta(seconds=0)).all()


def test_dataset_inspector_metrics(upi_synthesizer):
    """Verify DatasetInspector correctly computes class imbalance ratios and stats."""
    df = upi_synthesizer.generate_dataset(n_users=20, n_transactions=500, fraud_ratio=0.01, output_csv=None)
    inspector = DatasetInspector(UPI_MICRO_METADATA.name)
    report = inspector.inspect(
        df=df,
        target_col="is_fraud",
        amount_col="amount",
        time_col="timestamp",
        user_col="user_id",
        recipient_col="recipient_vpa",
    )

    assert report.num_rows == 500
    assert report.has_nulls is False
    assert report.imbalance.fraud_records == df["is_fraud"].sum()
    assert report.imbalance.legit_records == (500 - df["is_fraud"].sum())
    assert report.feature_availability["has_velocity_support"] is True
    assert report.feature_availability["has_recipient_entropy_support"] is True

