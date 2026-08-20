"""
August inference pipeline.

Loads all July-fitted artifacts as strictly read-only and processes August
windows through the identical code path used for July training.

CRITICAL INVARIANTS:
  - No artifact is updated, retrained, or adapted during inference.
  - The feature-computation code path is identical to July (same functions,
    different data — not a reimplementation).
  - Every loaded artifact's version is verified before inference begins.
  - Evidence is produced for EVERY August window (not just flagged ones).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa

from tads.models.evidence_taxonomy import DETECTOR_CATEGORY_MAP, EvidenceCategory

if TYPE_CHECKING:
    from pathlib import Path

    from tads.models.detectors.base import BaseAnomalyDetector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Manifest: describes the exact versions of all loaded artifacts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArtifactManifest:
    """
    Immutable record of every artifact loaded into the inference pipeline.
    Frozen=True ensures no mutation after construction.
    """

    detector_versions: dict[str, str]
    """Map of detector_name → version string, e.g. {"IForest": "if-v1"}."""

    pipeline_version: str
    """Overall pipeline version tag."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_version": self.pipeline_version,
            "detector_versions": dict(self.detector_versions),
        }

    def verify(self, expected: dict[str, str]) -> list[str]:
        """
        Compare loaded versions against expected versions.
        Returns a list of mismatch descriptions (empty = all match).
        """
        mismatches: list[str] = []
        for name, expected_ver in expected.items():
            loaded_ver = self.detector_versions.get(name)
            if loaded_ver is None:
                mismatches.append(f"Detector '{name}' not loaded (expected version '{expected_ver}')")
            elif loaded_ver != expected_ver:
                mismatches.append(
                    f"Detector '{name}' version mismatch: "
                    f"loaded='{loaded_ver}', expected='{expected_ver}'"
                )
        return mismatches


# ---------------------------------------------------------------------------
# Per-window inference result
# ---------------------------------------------------------------------------

@dataclass
class WindowResult:
    """The full evidence record for a single window."""

    window_index: int
    raw_scores: dict[str, float] = field(default_factory=dict)
    calibrated_evidence: dict[str, float] = field(default_factory=dict)
    ensemble_evidence: float = 0.0
    flagged: bool = False
    primary_category: str = ""
    explanation: str = ""


# ---------------------------------------------------------------------------
# The Pipeline
# ---------------------------------------------------------------------------

class AugustInferencePipeline:
    """
    Strictly read-only inference pipeline for August data.

    Loads frozen July artifacts (detectors with embedded calibrators and
    thresholds), runs August windows through the identical scoring code
    path, and produces per-window evidence for the full August dataset.

    There is no online learning, adaptive threshold, or artifact mutation
    anywhere in this class.
    """

    def __init__(
        self,
        detectors: dict[str, BaseAnomalyDetector],
        pipeline_version: str = "aug-inference-v1",
        ensemble_strategy: str = "max",
    ) -> None:
        """
        Args:
            detectors: Named detectors, already loaded with their frozen
                       July weights, calibrators, and thresholds.
            pipeline_version: Version tag for audit trails.
            ensemble_strategy: How to combine per-detector evidence
                               ('max', 'mean').
        """
        self.detectors = detectors
        self.pipeline_version = pipeline_version
        self.ensemble_strategy = ensemble_strategy

        # Build immutable manifest from loaded detector states
        det_versions = {name: det.version for name, det in detectors.items()}
        self.manifest = ArtifactManifest(
            detector_versions=det_versions,
            pipeline_version=pipeline_version,
        )

    # ------------------------------------------------------------------
    # Artifact verification
    # ------------------------------------------------------------------

    def verify_artifacts(self, expected_versions: dict[str, str]) -> None:
        """
        Verify every loaded artifact's version matches expected July versions.
        Raises ValueError on any mismatch.
        """
        mismatches = self.manifest.verify(expected_versions)
        if mismatches:
            raise ValueError(
                "Artifact version verification failed:\n  " + "\n  ".join(mismatches)
            )
        logger.info("All %d artifact versions verified successfully.", len(expected_versions))

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    def score_all(self, data: pa.Table) -> pa.Table:
        """
        Run all detectors on the input data and produce a unified evidence table.

        Returns a pa.Table with columns:
          - One `raw_score_{name}` column per detector
          - One `evidence_{name}` column per detector
          - `ensemble_evidence` (combined via the configured strategy)
          - `ensemble_flagged` (boolean, from the ensemble evidence)
          - `primary_category` (taxonomy category of the top-scoring detector)
          - `top_detector` (name of the detector with highest evidence)

        Evidence is produced for EVERY window, not just flagged ones.
        """
        len(data)
        all_columns: dict[str, list[Any]] = {}

        evidence_arrays: dict[str, np.ndarray] = {}

        for name, detector in self.detectors.items():
            if not detector.is_fitted:
                raise ValueError(f"Detector '{name}' is not fitted. Cannot run inference.")

            preds = detector.predict(data)

            raw = preds.column("raw_score").to_numpy()
            ev = preds.column("calibrated_evidence").to_numpy()

            all_columns[f"raw_score_{name}"] = raw.tolist()
            all_columns[f"evidence_{name}"] = ev.tolist()
            evidence_arrays[name] = ev

        # Combine evidence
        det_names = list(self.detectors.keys())
        ev_matrix = np.column_stack([evidence_arrays[n] for n in det_names])

        if self.ensemble_strategy == "max":
            ensemble_ev = np.max(ev_matrix, axis=1)
        elif self.ensemble_strategy == "mean":
            ensemble_ev = np.mean(ev_matrix, axis=1)
        else:
            raise ValueError(f"Unknown strategy: {self.ensemble_strategy}")

        # Determine which detector drove the ensemble score per window
        max_indices = np.argmax(ev_matrix, axis=1)
        top_detectors = [det_names[i] for i in max_indices]

        # Map top detector to taxonomy category
        primary_categories = []
        for det_name in top_detectors:
            det_class = type(self.detectors[det_name]).__name__
            cats = DETECTOR_CATEGORY_MAP.get(det_class, [EvidenceCategory.BEHAVIOURAL_ANOMALY])
            primary_categories.append(cats[0].value)

        # Use the minimum threshold across all detectors as ensemble threshold
        thresholds = [d.threshold for d in self.detectors.values()]
        ensemble_threshold = min(thresholds) if thresholds else 0.95

        ensemble_flagged = (ensemble_ev >= ensemble_threshold).tolist()

        all_columns["ensemble_evidence"] = ensemble_ev.tolist()
        all_columns["ensemble_flagged"] = ensemble_flagged
        all_columns["top_detector"] = top_detectors
        all_columns["primary_category"] = primary_categories

        return pa.table(all_columns)

    def run_sample_verification(
        self,
        sample_data: pa.Table,
        expected_versions: dict[str, str],
    ) -> pa.Table:
        """
        Validation gate: run inference on a tiny sample and verify artifacts.

        1. Verifies all artifact versions match expected.
        2. Runs inference on the sample.
        3. Logs summary statistics for human inspection.

        Returns the scored sample table.
        """
        logger.info("=== Sample Verification Gate ===")
        logger.info("Pipeline version: %s", self.pipeline_version)
        logger.info("Loaded detectors: %s", list(self.detectors.keys()))

        # Step 1: verify versions
        self.verify_artifacts(expected_versions)

        # Step 2: run inference
        results = self.score_all(sample_data)

        # Step 3: log summary
        logger.info("Sample size: %d windows", len(sample_data))
        for name in self.detectors:
            ev = results.column(f"evidence_{name}").to_numpy()
            logger.info(
                "  %s: evidence range [%.4f, %.4f], mean=%.4f",
                name, np.min(ev), np.max(ev), np.mean(ev),
            )

        ens_ev = results.column("ensemble_evidence").to_numpy()
        ens_flagged = results.column("ensemble_flagged").to_numpy(zero_copy_only=False)
        logger.info(
            "  Ensemble: evidence range [%.4f, %.4f], flagged=%d/%d",
            np.min(ens_ev), np.max(ens_ev),
            int(np.sum(ens_flagged)), len(ens_flagged),
        )

        logger.info("=== Sample Verification Passed ===")
        return results

    def save_manifest(self, path: Path) -> None:
        """Persist the pipeline manifest for audit."""
        path.write_text(json.dumps(self.manifest.to_dict(), indent=2))
