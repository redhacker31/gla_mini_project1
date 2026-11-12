"""Dataset Schema Inspector and Class Imbalance Analyzer.

Performs schema audit, missing value checks, and statistical distribution profiling
across fraud detection benchmark datasets.
"""
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


@dataclass
class ImbalanceSummary:
    total_records: int
    legit_records: int
    fraud_records: int
    fraud_percentage: float
    imbalance_ratio: str  # e.g., "1 : 587"


@dataclass
class AmountStats:
    mean: float
    std: float
    median: float
    p95: float
    p99: float
    min_val: float
    max_val: float
    skewness: float


@dataclass
class InspectionReport:
    dataset_name: str
    num_rows: int
    num_columns: int
    column_types: Dict[str, str]
    missing_values: Dict[str, int]
    has_nulls: bool
    imbalance: ImbalanceSummary
    legit_amount_stats: AmountStats
    fraud_amount_stats: AmountStats
    feature_availability: Dict[str, bool]
    limitations: List[str]


class DatasetInspector:
    """Performs deep statistical and structural inspection of fraud datasets."""

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name

    def inspect(
        self,
        df: pd.DataFrame,
        target_col: str,
        amount_col: str,
        time_col: Optional[str] = None,
        user_col: Optional[str] = None,
        recipient_col: Optional[str] = None,
        limitations: Optional[List[str]] = None,
    ) -> InspectionReport:
        """Inspect dataframe and produce a structured academic audit report."""
        num_rows, num_cols = df.shape
        col_types = {str(c): str(t) for c, t in df.dtypes.items()}
        missing = {str(c): int(s) for c, s in df.isnull().sum().items()}
        has_nulls = sum(missing.values()) > 0

        # Class imbalance calculation
        fraud_mask = df[target_col] == 1
        fraud_count = int(fraud_mask.sum())
        legit_count = num_rows - fraud_count
        fraud_pct = round((fraud_count / max(num_rows, 1)) * 100, 4)
        ratio_divisor = round(legit_count / max(fraud_count, 1), 1)
        imbalance = ImbalanceSummary(
            total_records=num_rows,
            legit_records=legit_count,
            fraud_records=fraud_count,
            fraud_percentage=fraud_pct,
            imbalance_ratio=f"1 : {ratio_divisor}",
        )

        # Amount statistics
        def _calc_stats(series: pd.Series) -> AmountStats:
            clean = series.dropna()
            if len(clean) == 0:
                return AmountStats(0, 0, 0, 0, 0, 0, 0, 0)
            return AmountStats(
                mean=round(float(clean.mean()), 2),
                std=round(float(clean.std()), 2),
                median=round(float(clean.median()), 2),
                p95=round(float(clean.quantile(0.95)), 2),
                p99=round(float(clean.quantile(0.99)), 2),
                min_val=round(float(clean.min()), 2),
                max_val=round(float(clean.max()), 2),
                skewness=round(float(clean.skew()), 2),
            )

        legit_amt_stats = _calc_stats(df.loc[~fraud_mask, amount_col])
        fraud_amt_stats = _calc_stats(df.loc[fraud_mask, amount_col])

        # Feature availability
        feature_avail = {
            "has_amount": amount_col in df.columns,
            "has_temporal_time": time_col is not None and time_col in df.columns,
            "has_user_identity": user_col is not None and user_col in df.columns,
            "has_recipient_identity": recipient_col is not None and recipient_col in df.columns,
            "has_velocity_support": bool(user_col and time_col and user_col in df.columns and time_col in df.columns),
            "has_recipient_entropy_support": bool(user_col and recipient_col and recipient_col in df.columns),
        }

        return InspectionReport(
            dataset_name=self.dataset_name,
            num_rows=num_rows,
            num_columns=num_cols,
            column_types=col_types,
            missing_values=missing,
            has_nulls=has_nulls,
            imbalance=imbalance,
            legit_amount_stats=legit_amt_stats,
            fraud_amount_stats=fraud_amt_stats,
            feature_availability=feature_avail,
            limitations=limitations or [],
        )
