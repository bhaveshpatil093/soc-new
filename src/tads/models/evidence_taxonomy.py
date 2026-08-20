"""
Evidence taxonomy constants.

Canonical Python representation of the evidence taxonomy defined in
docs/evidence_taxonomy.md.  All downstream code (Phase 9 episodes,
Phase 12 reports, explanation pipelines) MUST use these constants
rather than ad-hoc string literals.

IMPORTANT: No category in this module implies maliciousness, intent,
or attack.  Every category describes statistical or behavioural
unusualness relative to a frozen July baseline.
"""

from __future__ import annotations

import enum


class EvidenceCategory(enum.StrEnum):
    """
    The seven canonical evidence categories.

    Each value is a short, machine-readable identifier.  Human-readable
    descriptions live in the taxonomy document and in the DESCRIPTIONS
    dict below.
    """

    STATISTICAL_ANOMALY = "statistical_anomaly"
    """Feature value(s) with low probability under the July-fitted
    marginal distribution.  Per-feature, per-window."""

    BEHAVIOURAL_ANOMALY = "behavioural_anomaly"
    """Joint configuration of feature values that is unusual even if each
    individual value is unremarkable.  Multivariate."""

    TEMPORAL_ANOMALY = "temporal_anomaly"
    """Unusual transition or sequence relative to the preceding windows,
    even if the window's features would be unremarkable in isolation."""

    NOVEL_RELATIONSHIP = "novel_relationship"
    """Categorical entity or entity-relationship never observed in July.
    Novelty is an observational fact, NOT a security verdict."""

    DISTRIBUTIONAL_DRIFT = "distributional_drift"
    """Population-level shift between the July baseline and a subsequent
    observation period.  Distinct from any single-window evidence."""

    MODEL_DISAGREEMENT = "model_disagreement"
    """Calibrated evidence values from different detectors are
    substantially inconsistent for this window."""

    POTENTIAL_SECURITY_RELEVANCE = "potential_security_relevance"
    """Qualitative, human-facing judgment category.  Explicitly distinct
    from all statistical categories above.  Assigned by the triage or
    explanation layer, never by a detector directly."""


# ---------------------------------------------------------------------------
# Human-readable descriptions (for reports / logging)
# ---------------------------------------------------------------------------

DESCRIPTIONS: dict[EvidenceCategory, str] = {
    EvidenceCategory.STATISTICAL_ANOMALY: (
        "One or more feature values fall in the extreme tail of the "
        "July-fitted distribution for that feature."
    ),
    EvidenceCategory.BEHAVIOURAL_ANOMALY: (
        "The joint combination of feature values is unusual relative to "
        "July, even though individual features may be unremarkable."
    ),
    EvidenceCategory.TEMPORAL_ANOMALY: (
        "The transition from the preceding window sequence to this window "
        "is unusual relative to July's temporal patterns."
    ),
    EvidenceCategory.NOVEL_RELATIONSHIP: (
        "This window contains a categorical entity or entity-relationship "
        "that was never observed during the July baseline period."
    ),
    EvidenceCategory.DISTRIBUTIONAL_DRIFT: (
        "A population-level shift in feature distributions has been "
        "detected between the July baseline and the current observation "
        "period.  This is a model-health signal, not a per-window anomaly."
    ),
    EvidenceCategory.MODEL_DISAGREEMENT: (
        "The anomaly detectors substantially disagree on this window's "
        "evidence level, indicating epistemic uncertainty."
    ),
    EvidenceCategory.POTENTIAL_SECURITY_RELEVANCE: (
        "This window or episode may warrant security investigation based "
        "on the conjunction of evidence categories and domain context.  "
        "This is a human-facing judgment, not an automated classification."
    ),
}


# ---------------------------------------------------------------------------
# Detector → Category mapping  (mirrors the table in evidence_taxonomy.md)
# ---------------------------------------------------------------------------

DETECTOR_CATEGORY_MAP: dict[str, list[EvidenceCategory]] = {
    "RobustStatisticalDetector": [EvidenceCategory.STATISTICAL_ANOMALY],
    "IsolationForestDetector": [EvidenceCategory.BEHAVIOURAL_ANOMALY],
    "AutoencoderDetector": [EvidenceCategory.BEHAVIOURAL_ANOMALY],
    "PCADetector": [EvidenceCategory.BEHAVIOURAL_ANOMALY],
    "SequenceLSTMDetector": [EvidenceCategory.TEMPORAL_ANOMALY],
    "RarityDetector": [EvidenceCategory.NOVEL_RELATIONSHIP],
    "EnsembleDetector": [EvidenceCategory.MODEL_DISAGREEMENT],
}


def categories_for_detector(detector_class_name: str) -> list[EvidenceCategory]:
    """Return the taxonomy categories produced by a given detector class."""
    cats = DETECTOR_CATEGORY_MAP.get(detector_class_name)
    if cats is None:
        raise ValueError(
            f"Detector '{detector_class_name}' is not registered in the "
            f"evidence taxonomy.  Add it to DETECTOR_CATEGORY_MAP."
        )
    return cats
