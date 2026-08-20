"""
Rarity/novelty anomaly detector based on July frequency distributions.

This detector measures how rare or novel the categorical relationships
(e.g., user-IP, user-host) in a given window are relative to July.
High rarity/novelty does NOT inherently imply maliciousness; it simply
indicates a deviation from historical frequencies.

Raw scores represent information-theoretic surprisal (-log(P)) of the
observed categorical values. Unseen values are assigned a maximum
surprisal based on the size of the training set.

This detector is integrated into the standard calibration framework.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa

from tads.models.calibration import EmpiricalCalibrator
from tads.models.detectors.base import BaseAnomalyDetector

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class RarityDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Rarity/novelty detector.

    Calculates the surprisal of categorical feature combinations.
    Raw Score = Max surprisal across the monitored categorical features.
    """

    def __init__(
        self,
        feature_columns: list[str],
        unseen_penalty: float = 1.0,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            feature_columns: The categorical columns to measure rarity for.
            unseen_penalty: A multiplier applied to the max possible surprisal
                            when a completely novel relationship is observed.
        """
        super().__init__(**kwargs)
        self.feature_columns = feature_columns
        self.unseen_penalty = unseen_penalty

        # Maps feature_name -> {value -> surprisal_score}
        self._surprisal_tables: dict[str, dict[str, float]] = {}
        self._max_surprisal: dict[str, float] = {}

        self.calibrator: EmpiricalCalibrator | None = None

    def _extract_categorical(self, data: pa.Table) -> dict[str, list[str]]:
        """Extract categorical features as lists of strings."""
        missing = [f for f in self.feature_columns if f not in data.column_names]
        if missing:
            raise ValueError(f"Missing required categorical features: {missing}")

        features = {}
        for col in self.feature_columns:
            # Convert to string to handle various types robustly in dictionaries
            features[col] = [str(val) for val in data.column(col).to_pylist()]
        return features

    def _fit(self, data: pa.Table) -> None:
        """
        Build frequency tables and compute surprisal for July data.
        """
        features = self._extract_categorical(data)
        n_windows = len(data)

        # Base probability for an unseen event is roughly 1 / n_windows
        # (Laplace smoothing conceptually, though applied post-hoc)
        base_unseen_prob = 1.0 / max(n_windows, 1)
        base_unseen_surprisal = -np.log(base_unseen_prob) * self.unseen_penalty

        self._surprisal_tables = {}
        self._max_surprisal = {}

        for col, values in features.items():
            # Count frequencies
            counts: dict[str, int] = {}
            for val in values:
                counts[val] = counts.get(val, 0) + 1

            # Compute surprisal: -log(count / total)
            surprisal_map = {}
            for val, count in counts.items():
                prob = count / n_windows
                surprisal_map[val] = -np.log(prob)

            self._surprisal_tables[col] = surprisal_map
            self._max_surprisal[col] = base_unseen_surprisal

        logger.info(
            "Fitted rarity baselines for %d categorical features. Windows: %d",
            len(self.feature_columns),
            n_windows,
        )

    def score(self, data: pa.Table) -> pa.Array:
        """
        Score windows by rarity.
        Raw score is the MAX surprisal across all monitored features in the window.
        Higher score = more novel/rare.
        """
        if not self._surprisal_tables:
            raise ValueError("Detector is not fitted.")

        features = self._extract_categorical(data)
        n_windows = len(data)

        # Array of max surprisal per window
        max_surprisals = np.zeros(n_windows, dtype=np.float64)

        for col, values in features.items():
            table = self._surprisal_tables[col]
            unseen_val = self._max_surprisal[col]

            for i, val in enumerate(values):
                s = table.get(val, unseen_val)
                if s > max_surprisals[i]:
                    max_surprisals[i] = s

        return pa.array(max_surprisals.tolist())

    def fit_calibrator(self, data: pa.Table, threshold_evidence: float = 0.95) -> None:
        """Fit empirical calibrator on July raw surprisal scores."""
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
        Feature-level evidence: Returns the name and value of the
        relationship that drove the novelty score.
        """
        if not self._surprisal_tables:
            raise ValueError("Detector is not fitted.")

        features = self._extract_categorical(data)
        n_windows = len(data)

        max_surprisals = np.zeros(n_windows, dtype=np.float64)
        explanations = [""] * n_windows

        for col, values in features.items():
            table = self._surprisal_tables[col]
            unseen_val = self._max_surprisal[col]

            for i, val in enumerate(values):
                s = table.get(val, unseen_val)
                if s >= max_surprisals[i]:
                    max_surprisals[i] = s
                    novelty_type = "UNSEEN" if val not in table else f"RARE (Surprisal: {s:.2f})"
                    explanations[i] = f"Driven by {col}='{val}' [{novelty_type}]"

        return pa.array(explanations)

    def save(self, path: Path) -> None:
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted detector.")
        state = {
            "version": self.version,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "feature_columns": self.feature_columns,
            "unseen_penalty": self.unseen_penalty,
            "surprisal_tables": self._surprisal_tables,
            "max_surprisal": self._max_surprisal,
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
        self.unseen_penalty = state["unseen_penalty"]
        self._surprisal_tables = state["surprisal_tables"]
        self._max_surprisal = state["max_surprisal"]

        cal_scores = state.get("calibrator_sorted_scores")
        cal_threshold = state.get("calibrator_threshold")
        if cal_scores is not None and cal_threshold is not None:
            self.calibrator = EmpiricalCalibrator(
                model_version=self.version, threshold_evidence=cal_threshold
            )
            self.calibrator._sorted_scores = np.array(cal_scores)
            self.calibrator._n_scores = len(cal_scores)
            self.calibrator.is_fitted = True
