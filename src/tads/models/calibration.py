"""
Empirical calibration of anomaly detector raw scores using July score distributions.

Calibration maps raw detector scores to "evidence" values with a precise mathematical
meaning: evidence of X means "this window's raw score exceeds X fraction of all July
training windows' raw scores."

This is NOT a probability of being anomalous. It is a percentile rank within the
July-fitted empirical CDF. The distinction matters: evidence of 0.99 means
"more extreme than 99% of July," not "99% chance of being anomalous."

Calibration artifacts are frozen after fitting on July and versioned together with
the model version they were fitted against.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from tads.baselines.base import validate_baseline_temporal_bounds

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


class EmpiricalCalibrator:
    """
    Maps raw anomaly scores to calibrated evidence using the empirical CDF
    of July training scores.

    Mathematical definition:
        evidence(s) = fraction of July training scores <= s
                    = |{s_july : s_july <= s}| / |S_july|

    So evidence = 0.95 means: "this window's raw score exceeds 95% of
    July windows' raw scores."

    The calibrator stores a sorted array of July scores and uses binary search
    (np.searchsorted) for O(log n) lookup at inference time.

    This is NOT min-max normalization. The mapping is rank-based (percentile),
    not linear-scaling based. A raw score that equals the July median always
    maps to ~0.50 regardless of the min/max of the current scoring batch.
    """

    def __init__(self, model_version: str, threshold_evidence: float = 0.95) -> None:
        """
        Args:
            model_version: The detector model version this calibrator is tied to.
            threshold_evidence: The evidence level above which a window is flagged.
                Default 0.95 means "flag windows more extreme than 95% of July."
        """
        self.model_version = model_version
        self.threshold_evidence = threshold_evidence
        self.is_fitted = False
        self._sorted_scores: np.ndarray | None = None
        self._n_scores: int = 0

    def fit(
        self,
        raw_scores: pa.Array | np.ndarray,
        data: pa.Table | None = None,
        timestamp_col: str = "window_start",
    ) -> None:
        """
        Fit the calibrator on July raw scores.

        Args:
            raw_scores: The raw anomaly scores from scoring July training data.
            data: Optional. If provided, the temporal guard validates that
                  the data is strictly July-only.
            timestamp_col: Column name for temporal validation.
        """
        if self.is_fitted:
            raise ValueError("Calibrator is already fitted and frozen.")

        # Temporal guard: if the source data is provided, enforce July-only
        if data is not None:
            from datetime import UTC, datetime
            validate_baseline_temporal_bounds(
                data,
                datetime(2025, 8, 1, tzinfo=UTC),
                timestamp_col=timestamp_col,
            )

        scores_np = raw_scores.to_numpy() if isinstance(raw_scores, pa.Array) else np.asarray(raw_scores)

        # Sort and store the full empirical distribution
        self._sorted_scores = np.sort(scores_np)
        self._n_scores = len(self._sorted_scores)
        self.is_fitted = True

        logger.info(
            "Calibrator fitted on %d July scores. Score range: [%.4f, %.4f]",
            self._n_scores,
            self._sorted_scores[0],
            self._sorted_scores[-1],
        )

    def calibrate(self, raw_scores: pa.Array | np.ndarray) -> pa.Array:
        """
        Map raw scores to calibrated evidence using the frozen July empirical CDF.

        Returns a pyarrow Array of float64 evidence values in [0.0, 1.0].

        Mathematical meaning:
            evidence(s) = |{s_july : s_july <= s}| / N_july

        This is a pure lookup against frozen July state. It CANNOT modify
        the calibration distribution. There is no fit pathway here.
        """
        if not self.is_fitted or self._sorted_scores is None:
            raise ValueError("Calibrator has not been fitted.")

        scores_np = raw_scores.to_numpy() if isinstance(raw_scores, pa.Array) else np.asarray(raw_scores)

        # np.searchsorted with side='right' gives the count of sorted_scores <= each value
        ranks = np.searchsorted(self._sorted_scores, scores_np, side="right")
        evidence = ranks / self._n_scores

        return pa.array(evidence)

    def flag(self, evidence: pa.Array | np.ndarray) -> pa.Array:
        """
        Apply the frozen threshold to produce boolean anomaly flags.

        A window is flagged if its evidence >= threshold_evidence.
        """
        evidence_np = evidence.to_numpy() if isinstance(evidence, pa.Array) else np.asarray(evidence)

        flags = evidence_np >= self.threshold_evidence
        return pa.array(flags)

    def save(self, path: Path) -> None:
        """
        Persist the calibration artifact as a versioned JSON file.
        Includes the full sorted score array for exact round-tripping.
        """
        if not self.is_fitted or self._sorted_scores is None:
            raise ValueError("Cannot save an unfitted calibrator.")

        state = {
            "model_version": self.model_version,
            "threshold_evidence": self.threshold_evidence,
            "n_scores": self._n_scores,
            "sorted_scores": self._sorted_scores.tolist(),
        }

        path.write_text(json.dumps(state))
        logger.info("Calibrator saved to %s (%d scores)", path, self._n_scores)

    def load(self, path: Path) -> None:
        """Load a frozen calibration artifact."""
        if not path.exists():
            raise FileNotFoundError(f"Missing calibration artifact: {path}")

        state = json.loads(path.read_text())
        self.model_version = state["model_version"]
        self.threshold_evidence = state["threshold_evidence"]
        self._n_scores = state["n_scores"]
        self._sorted_scores = np.array(state["sorted_scores"])
        self.is_fitted = True

        logger.info(
            "Calibrator loaded from %s (version=%s, %d scores)",
            path,
            self.model_version,
            self._n_scores,
        )
