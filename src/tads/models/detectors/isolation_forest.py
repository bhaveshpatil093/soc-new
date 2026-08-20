"""
Isolation Forest anomaly detector.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import joblib
import pyarrow as pa
from sklearn.ensemble import IsolationForest

from tads.models.detectors.base import BaseAnomalyDetector

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class IsolationForestDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Isolation Forest anomaly detector.

    Trains exclusively on July data to discover structural anomalies via tree path lengths.
    Raw scores are NOT probabilities, but a relative ranking signal.
    """

    def __init__(
        self,
        feature_columns: list[str],
        n_estimators: int = 100,
        max_samples: int | str = "auto",
        max_features: float = 1.0,
        contamination: float | str = "auto",
        random_state: int = 42,
        n_jobs: int = -1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.feature_columns = feature_columns
        self.model = IsolationForest(
            n_estimators=n_estimators,
            max_samples=max_samples,
            max_features=max_features,
            contamination=contamination,
            random_state=random_state,
            n_jobs=n_jobs,
        )

    def _extract_features(self, data: pa.Table) -> Any:
        """Extracts the exact expected feature columns into a format sklearn can ingest."""
        # Note: In production with millions of rows, we might use pa.Table.to_pandas()
        # or zero-copy numpy conversions. For now, we ensure exact column matching.
        missing = [f for f in self.feature_columns if f not in data.column_names]
        if missing:
            raise ValueError(f"Missing required features for model input: {missing}")

        # Sklearn expects a 2D array-like of shape (n_samples, n_features)
        # Using pyarrow's native conversion to numpy is zero-copy/fast where possible
        features = []
        for col in self.feature_columns:
            arr = data.column(col).to_numpy()
            features.append(arr)

        import numpy as np
        return np.column_stack(features)

    def _fit(self, data: pa.Table) -> None:
        """
        Fits the Isolation Forest on the extracted July features.
        """
        x_features = self._extract_features(data)
        self.model.fit(x_features)

    def score(self, data: pa.Table) -> pa.Array:
        """
        Scores the input data using the trained Isolation Forest.

        CRITICAL WARNING: The raw score is derived from tree path lengths.
        It is a relative ranking signal, NOT a calibrated probability.

        Sklearn's score_samples returns negative anomaly scores (where lower/more negative
        means more anomalous). We negate this output so that HIGHER = MORE ANOMALOUS,
        matching our global semantics.

        Min-Max normalization is explicitly prohibited.
        """
        x_features = self._extract_features(data)

        # score_samples: The anomaly score of the input samples.
        # The lower, the more abnormal.
        raw_negative_scores = self.model.score_samples(x_features)

        # Negate so higher is more anomalous
        import numpy as np
        inverted_scores = np.negative(raw_negative_scores)

        return pa.array(inverted_scores)

    def explain(self, data: pa.Table) -> pa.Array:
        """
        Explainability is deferred for tree ensembles in Phase 6 base implementation.
        """
        return pa.array(["Explanation deferred."] * len(data))

    def save(self, path: Path) -> None:
        """
        Persist the model and its preprocessing (feature_columns) as a single coupled artifact
        using joblib, ensuring perfect mathematical round-tripping.
        """
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted detector.")

        state = {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "feature_columns": self.feature_columns,
            "model": self.model,
        }

        # We save directly to the given path, expecting it to be a .joblib file
        # The caller is responsible for providing a .joblib path
        if path.suffix != ".joblib":
            logger.warning(f"Saving IsolationForest to a non-joblib extension: {path.suffix}")

        joblib.dump(state, path)

    def load(self, path: Path) -> None:
        """
        Load the coupled model and preprocessing artifact.
        """
        if not path.exists():
            raise FileNotFoundError(f"Missing model artifact: {path}")

        state = joblib.load(path)

        self.version = state["version"]
        self.threshold = state["threshold"]
        self.is_fitted = state["is_fitted"]
        self.feature_columns = state["feature_columns"]
        self.model = state["model"]
