"""
PCA reconstruction anomaly detector.

Learns the principal components of July training data and uses the
mean squared reconstruction error (MSE) as the anomaly score.

The number of components is dynamically chosen based on a target
explained variance threshold (e.g., 95%) rather than hardcoded.

CRITICAL: The raw score is a reconstruction error magnitude,
NOT a probability. Higher error = more anomalous.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa
from sklearn.decomposition import PCA

from tads.models.calibration import EmpiricalCalibrator
from tads.models.detectors.base import BaseAnomalyDetector

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class PCADetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    PCA-based reconstruction anomaly detector.

    Determines optimal dimensionality based on target explained variance.
    Raw score = Mean Squared Error between original and PCA-reconstructed features.
    """

    def __init__(
        self,
        feature_columns: list[str],
        target_explained_variance: float = 0.95,
        val_split_frac: float = 0.2,
        seed: int = 42,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.feature_columns = feature_columns
        self.target_explained_variance = target_explained_variance
        self.val_split_frac = val_split_frac
        self.seed = seed

        self._pca: PCA | None = None
        self._feature_means: np.ndarray | None = None
        self._feature_stds: np.ndarray | None = None

        self.n_components_: int | None = None
        self.explained_variance_ratio_: float | None = None

        self.calibrator: EmpiricalCalibrator | None = None

    def _extract_features(self, data: pa.Table) -> np.ndarray:
        """Extract feature columns into a numpy array."""
        missing = [f for f in self.feature_columns if f not in data.column_names]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        arrays = []
        for col in self.feature_columns:
            arrays.append(data.column(col).to_numpy().astype(np.float32))
        return np.column_stack(arrays)

    def _standardize(self, x: np.ndarray, fit: bool = False) -> np.ndarray:
        """
        Z-score standardization using robust stats if possible,
        but for PCA standard mean/std is mathematically aligned.
        We'll stick to standard mean/std here for strict PCA.
        """
        if fit:
            self._feature_means = np.mean(x, axis=0)
            self._feature_stds = np.std(x, axis=0)
            # Prevent division by zero
            self._feature_stds[self._feature_stds < 1e-8] = 1.0

        if self._feature_means is None or self._feature_stds is None:
            raise ValueError("Standardization parameters not fitted.")

        return (x - self._feature_means) / self._feature_stds

    def _fit(self, data: pa.Table) -> None:
        """
        Fit PCA on July data.
        Selects n_components to reach target_explained_variance.
        """
        raw_features = self._extract_features(data)
        n_samples = len(raw_features)

        # Chronological split for evaluating stable reconstruction
        split_idx = int(n_samples * (1 - self.val_split_frac))
        train_raw = raw_features[:split_idx]
        val_raw = raw_features[split_idx:]

        # Fit standardization on training split only
        train_std = self._standardize(train_raw, fit=True)
        val_std = self._standardize(val_raw, fit=False)

        # Fit full PCA to find explained variance
        full_pca = PCA(random_state=self.seed)
        full_pca.fit(train_std)

        cumulative_variance = np.cumsum(full_pca.explained_variance_ratio_)
        # Find first index where cumulative variance >= target
        n_components = int(np.argmax(cumulative_variance >= self.target_explained_variance)) + 1

        # If target is never reached exactly (due to floating point precision), use all
        if n_components == 1 and cumulative_variance[0] < self.target_explained_variance:
             n_components = len(cumulative_variance)

        self.n_components_ = n_components
        self.explained_variance_ratio_ = float(cumulative_variance[n_components - 1])

        # Refit PCA with chosen components
        self._pca = PCA(n_components=self.n_components_, random_state=self.seed)
        self._pca.fit(train_std)

        # Validation MSE purely for logging/sanity check
        val_transformed = self._pca.transform(val_std)
        val_reconstructed = self._pca.inverse_transform(val_transformed)
        val_mse = np.mean((val_std - val_reconstructed) ** 2)

        logger.info(
            "PCA fitted. Retained %d components (%.2f%% variance). Val MSE: %.6f",
            self.n_components_,
            self.explained_variance_ratio_ * 100,
            val_mse,
        )

    def score(self, data: pa.Table) -> pa.Array:
        """
        Score windows by mean squared reconstruction error.
        Higher error = more anomalous.
        """
        if self._pca is None:
            raise ValueError("PCA model not fitted.")

        raw_features = self._extract_features(data)
        std_features = self._standardize(raw_features, fit=False)

        transformed = self._pca.transform(std_features)
        reconstructed = self._pca.inverse_transform(transformed)

        # Mean squared error per window (across all features)
        mse = np.mean((std_features - reconstructed) ** 2, axis=1)

        return pa.array(mse.tolist())

    def fit_calibrator(self, data: pa.Table, threshold_evidence: float = 0.95) -> None:
        """Fit the empirical calibrator on July raw scores."""
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
        Returns feature-level breakdown of reconstruction error.
        """
        if self._pca is None:
            raise ValueError("PCA model not fitted.")

        raw_features = self._extract_features(data)
        std_features = self._standardize(raw_features, fit=False)

        transformed = self._pca.transform(std_features)
        reconstructed = self._pca.inverse_transform(transformed)

        sq_error = (std_features - reconstructed) ** 2

        explanations = []
        for i in range(len(data)):
            errors = sq_error[i]
            parts = [
                f"{self.feature_columns[j]}={errors[j]:.4f}"
                for j in range(len(self.feature_columns))
            ]
            explanations.append("recon_error: " + ", ".join(parts))

        return pa.array(explanations)

    def save(self, path: Path) -> None:
        """
        Persist PCA model and preprocessing as one artifact.
        Since PCA isn't easily JSON serializable via standard dicts,
        we serialize its matrix components manually.
        """
        if not self.is_fitted or self._pca is None:
            raise ValueError("Cannot save an unfitted detector.")

        state = {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "feature_columns": self.feature_columns,
            "target_explained_variance": self.target_explained_variance,
            "n_components_": self.n_components_,
            "explained_variance_ratio_": self.explained_variance_ratio_,
            "seed": self.seed,
            "feature_means": self._feature_means.tolist() if self._feature_means is not None else None,
            "feature_stds": self._feature_stds.tolist() if self._feature_stds is not None else None,

            # PCA Internal State
            "pca_components_": self._pca.components_.tolist(),
            "pca_mean_": self._pca.mean_.tolist(),

            # Calibrator
            "calibrator_sorted_scores": (
                self.calibrator._sorted_scores.tolist()
                if self.calibrator is not None and self.calibrator._sorted_scores is not None
                else None
            ),
            "calibrator_threshold": (
                self.calibrator.threshold_evidence
                if self.calibrator is not None
                else None
            ),
        }

        import joblib

        if path.suffix != ".joblib":
            logger.warning(f"Saving PCADetector to non-joblib path: {path}")

        # We will use joblib for full exact reconstruction of the PCA object
        # but store our metadata wrapped around it
        dump_state = {
            "metadata": state,
            "pca_model": self._pca
        }
        joblib.dump(dump_state, path)

    def load(self, path: Path) -> None:
        """Load PCA model from joblib artifact."""
        if not path.exists():
            raise FileNotFoundError(f"Missing model artifact: {path}")

        import joblib

        dump_state = joblib.load(path)
        state = dump_state["metadata"]

        self.version = state["version"]
        self.threshold = state["threshold"]
        self.is_fitted = state["is_fitted"]
        self.feature_columns = state["feature_columns"]
        self.target_explained_variance = state["target_explained_variance"]
        self.n_components_ = state["n_components_"]
        self.explained_variance_ratio_ = state["explained_variance_ratio_"]
        self.seed = state["seed"]

        if state["feature_means"] is not None:
            self._feature_means = np.array(state["feature_means"], dtype=np.float32)
        if state["feature_stds"] is not None:
            self._feature_stds = np.array(state["feature_stds"], dtype=np.float32)

        self._pca = dump_state["pca_model"]

        cal_scores = state.get("calibrator_sorted_scores")
        cal_threshold = state.get("calibrator_threshold")
        if cal_scores is not None and cal_threshold is not None:
            self.calibrator = EmpiricalCalibrator(
                model_version=self.version, threshold_evidence=cal_threshold
            )
            self.calibrator._sorted_scores = np.array(cal_scores)
            self.calibrator._n_scores = len(cal_scores)
            self.calibrator.is_fitted = True
