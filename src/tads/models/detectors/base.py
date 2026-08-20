"""
Common interface for Anomaly Detectors.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc

from tads.baselines.base import ImmutableBaselineError, validate_baseline_temporal_bounds

if TYPE_CHECKING:
    from pathlib import Path


class BaseAnomalyDetector(ABC):
    """
    Unified interface for all Phase 6 anomaly detectors.

    Enforces strict temporal separation during `fit()` (July data only) and provides
    standardized `score()` and `predict()` methods.
    """

    def __init__(self, version: str = "v1.0", threshold: float = 1.0, training_end_bound: datetime | None = None) -> None:
        self.version = version
        self.threshold = threshold
        self.is_fitted = False
        # Default bound: August 1st, 2025 UTC
        self.training_end_bound = training_end_bound or datetime(2025, 8, 1, tzinfo=UTC)
        self.state: dict[str, Any] = {}

    def fit(self, data: pa.Table, timestamp_col: str = "window_start") -> None:
        """
        Fits the detector on training data.
        Enforces TemporalGuard pattern to prevent August data leakage.
        """
        if self.is_fitted:
            raise ImmutableBaselineError("Detector is already fitted and frozen.")

        validate_baseline_temporal_bounds(data, self.training_end_bound, timestamp_col=timestamp_col)
        self._fit(data)
        self.is_fitted = True

    @abstractmethod
    def _fit(self, data: pa.Table) -> None:
        """Internal fit implementation."""
        pass

    @abstractmethod
    def score(self, data: pa.Table) -> pa.Array:
        """
        Returns the raw, uncalibrated scores for each window.
        Must return a pyarrow Array of floats.
        """
        pass

    def predict(self, data: pa.Table) -> pa.Table:
        """
        Orchestrates inference.
        Returns a pyarrow Table with standardized columns:
          - raw_score
          - calibrated_evidence
          - anomaly
          - model_version
        """
        if not self.is_fitted:
            raise ValueError("Cannot predict with an unfitted detector.")

        raw_scores = self.score(data)

        # In Phase 6/7, calibrated_evidence mapping will be sophisticated.
        # For the base interface, we defer calibration to subclass or 1:1 mapping.
        calibrated = self._calibrate(raw_scores)

        # Anomaly is derived from calibrated_evidence and frozen threshold
        anomalies = pc.greater_equal(calibrated, self.threshold)

        # Model version array
        versions = pa.array([self.version] * len(data))

        return pa.table({
            "raw_score": raw_scores,
            "calibrated_evidence": calibrated,
            "anomaly": anomalies,
            "model_version": versions
        })

    def _calibrate(self, raw_scores: pa.Array) -> pa.Array:
        """
        Maps raw scores to calibrated evidence.
        Subclasses can override this if they have internal calibration,
        or it will be mapped globally later.
        By default, we assume raw_scores are the calibrated_evidence.
        """
        return raw_scores

    @abstractmethod
    def explain(self, data: pa.Table) -> pa.Array:
        """
        Returns structural reasons or feature attributions for the anomaly score.
        Must return a pyarrow Array of strings/structs.
        """
        pass

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration and state."""
        return {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "state": self.state
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Deserialize configuration and state."""
        self.version = data["version"]
        self.threshold = data["threshold"]
        self.is_fitted = data["is_fitted"]
        self.state = data["state"]

    def save(self, path: Path) -> None:
        """
        Saves the detector state.
        Must ensure exact round-trip serialization.
        """
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted detector.")

        path.write_text(json.dumps(self.to_dict(), indent=2))

    def load(self, path: Path) -> None:
        """Loads the detector state."""
        if not path.exists():
            raise FileNotFoundError(f"Missing model file: {path}")

        raw_state = json.loads(path.read_text())
        self.from_dict(raw_state)
