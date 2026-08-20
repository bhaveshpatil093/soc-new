"""
Robust statistical anomaly detector based on July feature distributions.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa
from scipy import stats

from tads.models.calibration import EmpiricalCalibrator
from tads.models.detectors.base import BaseAnomalyDetector

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class RobustStatisticalDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Robust statistical anomaly detector.

    Uses deviation from frozen July baselines (robust z-score using Median and MAD)
    combined into a per-window score (max absolute robust z-score across all features).

    Returns feature-level evidence (which specific feature drove the score) in the
    explain() method.
    """

    def __init__(
        self,
        feature_columns: list[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.feature_columns = feature_columns

        # Fitted statistics per feature
        self._feature_medians: np.ndarray | None = None
        self._feature_mads: np.ndarray | None = None

        self.calibrator: EmpiricalCalibrator | None = None

    def _extract_features(self, data: pa.Table) -> np.ndarray:
        """Extract feature columns into (n_windows, n_features) array."""
        missing = [f for f in self.feature_columns if f not in data.column_names]
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        arrays = [data.column(col).to_numpy().astype(np.float64) for col in self.feature_columns]
        return np.column_stack(arrays)

    def _fit(self, data: pa.Table) -> None:
        """
        Fit robust statistics (Median and MAD) on July data.
        """
        raw = self._extract_features(data)
        self._feature_medians = np.nanmedian(raw, axis=0)
        self._feature_mads = stats.median_abs_deviation(raw, axis=0, nan_policy="omit")

        # Prevent division by zero for constant features by setting MAD to 1.0 where it's 0.
        # If MAD is 0, it means >50% of the values are identical to the median.
        # We can substitute a small epsilon or 1.0 to avoid NaNs. We use 1.0.
        self._feature_mads[self._feature_mads < 1e-8] = 1.0

        logger.info(
            "Fitted robust stats for %d features. Medians: %s, MADs: %s",
            len(self.feature_columns),
            self._feature_medians,
            self._feature_mads,
        )

    def _compute_robust_z_scores(self, data: pa.Table) -> np.ndarray:
        """Compute robust z-scores for all features."""
        if self._feature_medians is None or self._feature_mads is None:
            raise ValueError("Detector is not fitted.")

        raw = self._extract_features(data)
        # Robust Z-Score = |x - median| / MAD
        z_scores = np.abs(raw - self._feature_medians) / self._feature_mads
        return z_scores

    def score(self, data: pa.Table) -> pa.Array:
        """
        Score windows by the MAX absolute robust z-score across all features.
        This means a window is as anomalous as its most extreme feature.

        The raw score is a distance metric (MAD units), NOT a probability.
        Higher score = more anomalous.
        """
        z_scores = self._compute_robust_z_scores(data)
        # Score is the max deviation across all monitored features
        max_z_scores = np.max(z_scores, axis=1)
        return pa.array(max_z_scores.tolist())

    def fit_calibrator(self, data: pa.Table, threshold_evidence: float = 0.95) -> None:
        """Fit empirical calibrator on July scores."""
        raw_scores = self.score(data)
        self.calibrator = EmpiricalCalibrator(
            model_version=self.version, threshold_evidence=threshold_evidence
        )
        self.calibrator.fit(raw_scores, data=data)
        self.threshold = threshold_evidence

    def _calibrate(self, raw_scores: pa.Array) -> pa.Array:
        if self.calibrator is not None and self.calibrator.is_fitted:
            return self.calibrator.calibrate(raw_scores)
        return raw_scores

    def explain(self, data: pa.Table) -> pa.Array:
        """
        Feature-level evidence: Returns the name and robust z-score of the
        feature that drove the maximum score for each window.
        """
        z_scores = self._compute_robust_z_scores(data)
        max_feature_indices = np.argmax(z_scores, axis=1)
        max_z_scores = np.max(z_scores, axis=1)

        explanations = []
        for i, f_idx in enumerate(max_feature_indices):
            feature_name = self.feature_columns[f_idx]
            z = max_z_scores[i]
            explanations.append(f"Driven by {feature_name} (Robust Z-Score: {z:.2f})")

        return pa.array(explanations)

    def save(self, path: Path) -> None:
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted detector.")
        state = {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "feature_columns": self.feature_columns,
            "feature_medians": self._feature_medians.tolist() if self._feature_medians is not None else None,
            "feature_mads": self._feature_mads.tolist() if self._feature_mads is not None else None,
            "calibrator_sorted_scores": (
                self.calibrator._sorted_scores.tolist()
                if self.calibrator is not None and self.calibrator._sorted_scores is not None
                else None
            ),
            "calibrator_threshold": (
                self.calibrator.threshold_evidence if self.calibrator is not None else None
            ),
        }
        path.write_text(json.dumps(state))

    def load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Missing model artifact: {path}")
        state = json.loads(path.read_text())
        self.version = state["version"]
        self.threshold = state["threshold"]
        self.is_fitted = state["is_fitted"]
        self.feature_columns = state["feature_columns"]
        if state["feature_medians"] is not None:
            self._feature_medians = np.array(state["feature_medians"], dtype=np.float64)
        if state["feature_mads"] is not None:
            self._feature_mads = np.array(state["feature_mads"], dtype=np.float64)

        cal_scores = state.get("calibrator_sorted_scores")
        cal_threshold = state.get("calibrator_threshold")
        if cal_scores is not None and cal_threshold is not None:
            self.calibrator = EmpiricalCalibrator(
                model_version=self.version, threshold_evidence=cal_threshold
            )
            self.calibrator._sorted_scores = np.array(cal_scores)
            self.calibrator._n_scores = len(cal_scores)
            self.calibrator.is_fitted = True
