"""Real-Time ML Anomaly Detection Service for FastAPI Gateway.

Loads the trained Isolation Forest pipeline and computes normalized
anomaly scores S_ml in [0.0, 1.0] within a sub-15ms inference budget.
"""
from typing import Dict, List, Optional
import os
import time
import joblib
import numpy as np


class AnomalyDetectorService:
    """Manages the serialized Isolation Forest model and inference lifecycle."""

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            # Default location relative to backend or project root
            candidates = [
                os.path.abspath("ml/artifacts/isolation_forest_pipeline.joblib"),
                os.path.abspath("../ml/artifacts/isolation_forest_pipeline.joblib"),
                os.path.abspath("../../ml/artifacts/isolation_forest_pipeline.joblib"),
            ]
            self.model_path = next((c for c in candidates if os.path.exists(c)), candidates[0])
        else:
            self.model_path = model_path

        self.model = None
        self.scaler = None
        self.feature_names = []
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        """Load serialized model bundle if present."""
        if os.path.exists(self.model_path):
            try:
                bundle = joblib.load(self.model_path)
                self.scaler = bundle.get("scaler")
                self.model = bundle.get("model")
                self.feature_names = bundle.get("feature_names", [])
                self.is_loaded = True
            except Exception as e:
                print(f"[WARN] Failed to load Isolation Forest from {self.model_path}: {e}")
                self.is_loaded = False

    def predict_anomaly_score(self, feature_vector: np.ndarray) -> float:
        """Predict normalized anomaly score S_ml in [0.0, 1.0] for a 1D or 2D feature array.
        
        Score Interpretation:
          - S_ml ~ 0.0: Deep within legitimate cluster (routine micro-commerce).
          - S_ml ~ 0.5: Near decision boundary.
          - S_ml > 0.7: Strong anomaly / rapid velocity outlier.
        """
        if feature_vector.ndim == 1:
            features = feature_vector.reshape(1, -1)
        else:
            features = feature_vector

        # 1. Primary Model Inference
        if self.is_loaded and self.model is not None:
            import pandas as pd
            if self.scaler is not None:
                if self.feature_names and len(self.feature_names) == features.shape[1]:
                    feat_df = pd.DataFrame(features, columns=self.feature_names)
                    scaled_feats = self.scaler.transform(feat_df)
                else:
                    scaled_feats = self.scaler.transform(features)
            else:
                scaled_feats = features
            raw_decision = self.model.decision_function(scaled_feats)[0]
            # Normalized score: clip(0.5 - raw_decision, 0.0, 1.0)
            score = float(np.clip(0.5 - raw_decision, 0.0, 1.0))
            return round(score, 4)

        # 2. Heuristic Statistical Fallback (if model artifact not yet generated)
        # Vector order: [amount, count_5m, count_1h, count_24h, sum_5m, sum_1h, delta_t, entropy_1h, amt_ratio]
        count_5m = float(features[0, 1])
        delta_t = float(features[0, 6])
        entropy = float(features[0, 7])
        amount = float(features[0, 0])

        score = 0.15  # Base routine baseline
        if count_5m >= 5:
            score += 0.45
        elif count_5m >= 3:
            score += 0.25

        if delta_t < 30.0:
            score += 0.20
        elif delta_t < 60.0:
            score += 0.10

        if entropy > 1.5:
            score += 0.15

        if amount > 500.0:
            score += 0.10

        return round(float(np.clip(score, 0.0, 1.0)), 4)


# Singleton instance for backend runtime
anomaly_detector_service = AnomalyDetectorService()
