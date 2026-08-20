"""
Principled Ensemble Anomaly Detector.

Combines the outputs of multiple heterogeneous sub-detectors (Isolation Forest,
PCA, Autoencoder, Sequence LSTM, Rarity, etc.) into a unified evidence score.

Crucially, it does NOT average raw scores (which are non-comparable). Instead,
it extracts the fully calibrated `calibrated_evidence` (percentiles) from each
sub-detector and combines those mathematically comparable values.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa

from tads.models.detectors.base import BaseAnomalyDetector

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class EnsembleDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Ensemble anomaly detector using calibrated evidence combinations.
    """

    def __init__(
        self,
        detectors: dict[str, BaseAnomalyDetector],
        strategy: str = "max",
        weights: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            detectors: A dictionary mapping detector names to instantiated BaseAnomalyDetector objects.
            strategy: The combination strategy ('max', 'mean', 'weighted').
            weights: Optional dictionary of weights for the 'weighted' strategy.
        """
        super().__init__(**kwargs)
        self.detectors = detectors
        self.strategy = strategy.lower()
        self.weights = weights

        if not self.detectors:
            raise ValueError("Ensemble must contain at least one detector.")

        if self.strategy not in ("max", "mean", "weighted"):
            raise ValueError(f"Unknown combination strategy: {self.strategy}")

        if self.strategy == "weighted":
            if not self.weights:
                raise ValueError("Weights must be provided for 'weighted' strategy.")
            if set(self.weights.keys()) != set(self.detectors.keys()):
                raise ValueError("Keys in 'weights' must perfectly match keys in 'detectors'.")

    def _fit(self, data: pa.Table) -> None:
        """
        Fit all sub-detectors and their empirical calibrators on the July data.
        """
        for name, detector in self.detectors.items():
            logger.info(f"Ensemble fitting sub-detector: {name}...")
            # We enforce standard threshold=0.95 for internal calibration of sub-detectors
            # The ensemble itself will have its own global threshold applied later.
            detector.fit(data)

            # Since the ensemble relies exclusively on calibrated evidence to combine,
            # we MUST ensure the sub-detectors have their empirical calibrators fitted.
            if hasattr(detector, "fit_calibrator"):
                detector.fit_calibrator(data, threshold_evidence=0.95)
            else:
                logger.warning(f"Detector {name} lacks fit_calibrator(), raw scores will be used directly (DANGEROUS).")

        logger.info(f"Ensemble successfully fitted {len(self.detectors)} detectors.")

    def _get_all_calibrated_evidence(self, data: pa.Table) -> dict[str, np.ndarray]:
        """Runs inference on all sub-detectors and returns their calibrated evidence."""
        evidence_map = {}
        for name, detector in self.detectors.items():
            if not detector.is_fitted:
                raise ValueError(f"Sub-detector {name} is not fitted.")

            preds = detector.predict(data)
            evidence = preds.column("calibrated_evidence").to_numpy()
            evidence_map[name] = evidence

        return evidence_map

    def score(self, data: pa.Table) -> pa.Array:
        """
        The Ensemble's 'raw' score is actually the combined calibrated evidence.
        Because we combine percentiles, the output is already strictly in [0, 1].
        """
        evidence_map = self._get_all_calibrated_evidence(data)
        len(data)

        # Convert to matrix of shape (n_windows, n_detectors)
        evidence_matrix = np.column_stack([evidence_map[name] for name in self.detectors])

        if self.strategy == "max":
            combined = np.max(evidence_matrix, axis=1)
        elif self.strategy == "mean":
            combined = np.mean(evidence_matrix, axis=1)
        elif self.strategy == "weighted":
            assert self.weights is not None
            weight_arr = np.array([self.weights[name] for name in self.detectors])
            # Normalize weights to sum to 1
            weight_arr = weight_arr / np.sum(weight_arr)
            combined = np.sum(evidence_matrix * weight_arr, axis=1)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        return pa.array(combined.tolist())

    def _calibrate(self, raw_scores: pa.Array) -> pa.Array:
        """
        The ensemble score is ALREADY calibrated evidence because it combines [0, 1] mapped inputs.
        We do not re-calibrate it empirically.
        """
        return raw_scores

    def explain(self, data: pa.Table) -> pa.Array:
        """
        Extracts the explanation from the detector that provided the highest evidence
        (most relevant for 'max' strategy).
        """
        evidence_map = self._get_all_calibrated_evidence(data)
        names = list(self.detectors.keys())

        # Shape: (n_windows, n_detectors)
        evidence_matrix = np.column_stack([evidence_map[name] for name in names])

        # Index of max detector per window
        max_indices = np.argmax(evidence_matrix, axis=1)
        max_evidences = np.max(evidence_matrix, axis=1)

        # Pre-calculate sub-explanations (this can be expensive but ensures correctness)
        sub_explanations = {}
        for name, detector in self.detectors.items():
            sub_explanations[name] = detector.explain(data)

        explanations = []
        for i in range(len(data)):
            max_idx = max_indices[i]
            max_name = names[max_idx]
            max_ev = max_evidences[i]

            sub_expl = sub_explanations[max_name][i].as_py()
            explanations.append(f"[{max_name} (Evidence {max_ev:.2f})]: {sub_expl}")

        return pa.array(explanations)

    def save(self, path: Path) -> None:
        """
        Saves the ensemble and delegates saving to all child detectors.
        Since children might be joblib or json, we require path to be a directory.
        """
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted detector.")

        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)

        state = {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "strategy": self.strategy,
            "weights": self.weights,
            "detector_names": list(self.detectors.keys()),
        }

        metadata_path = path / "ensemble_metadata.json"
        metadata_path.write_text(json.dumps(state, indent=2))

        # Save sub-detectors
        for name, detector in self.detectors.items():
            # Use specific extensions if necessary (e.g., joblib for PCA)
            ext = ".joblib" if hasattr(detector, "_pca") else ".json"
            child_path = path / f"sub_{name}{ext}"
            detector.save(child_path)

    def load(self, path: Path) -> None:
        """
        Loads the ensemble metadata and delegates loading to child detectors.
        """
        if not path.is_dir():
            raise NotADirectoryError(f"Ensemble artifact must be a directory: {path}")

        metadata_path = path / "ensemble_metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Missing ensemble metadata: {metadata_path}")

        state = json.loads(metadata_path.read_text())

        self.version = state["version"]
        self.threshold = state["threshold"]
        self.is_fitted = state["is_fitted"]
        self.strategy = state["strategy"]
        self.weights = state["weights"]

        expected_names = state["detector_names"]

        if not self.detectors:
            raise ValueError(
                "EnsembleDetector must be instantiated with the correct sub-detector "
                "objects mapping before calling load()."
            )

        if set(expected_names) != set(self.detectors.keys()):
            raise ValueError(
                f"Mismatch in loaded detectors. Expected {expected_names}, got {list(self.detectors.keys())}"
            )

        # Load sub-detectors
        for name, detector in self.detectors.items():
            ext = ".joblib" if hasattr(detector, "_pca") else ".json"
            child_path = path / f"sub_{name}{ext}"
            detector.load(child_path)
