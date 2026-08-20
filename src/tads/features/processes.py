"""
Process-centric behavioral features.

These features capture entity-level activity focused on processes (executables),
including diversity, concentration, parent-child relationships, and command-line
pattern analysis.
"""
from __future__ import annotations

import re
from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)
from tads.features.utils import (
    average_distinct_per_entity,
    calculate_entropy,
    calculate_hhi,
    calculate_historical_deviation,
)


def normalize_cmdline(cmd: str | None) -> str:
    """
    Normalizes a command line by abstracting away highly variable components
    such as PIDs, timestamps, temporary file paths, UUIDs, IPs, and hashes.

    Produces a structural "pattern" of the command execution.
    """
    if not cmd:
        return "unknown"

    cmd = cmd.lower()

    # 1. Mask UUIDs
    cmd = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', cmd)
    # 2. Mask IPs
    cmd = re.sub(r'\b\d{1,3}(\.\d{1,3}){3}\b', '<IP>', cmd)
    # 3. Mask obvious hex strings / hashes (8 or more hex characters)
    cmd = re.sub(r'\b[0-9a-f]{8,}\b', '<HEX>', cmd)
    # 4. Mask pure numbers (e.g. PIDs, ports, timestamps)
    cmd = re.sub(r'\b\d+\b', '<NUM>', cmd)

    # 5. Mask paths
    tokens = []
    # Use split to evaluate token by token
    for token in cmd.split():
        # Heuristic for file paths: contains slashes (Unix/Windows) or starts with a drive letter
        if ('/' in token) or ('\\' in token and not token.startswith('-')) or re.match(r'^[a-z]:\\', token):
            tokens.append('<PATH>')
        else:
            tokens.append(token)

    normalized = " ".join(tokens)
    # Strip extra whitespace
    return re.sub(r'\s+', ' ', normalized).strip()


class ActiveProcessesFeature(BaseFeature):  # type: ignore[misc]
    """Count of distinct processes in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="active_processes",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_name"],
            mathematical_definition="COUNT(DISTINCT process_name)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        procs = {e.get("process_name") or "unknown" for e in events}
        count = len(procs) if events else 0.0
        return {"active_processes": float(count)}


class ProcessEventConcentrationFeature(BaseFeature):  # type: ignore[misc]
    """
    Herfindahl-Hirschman Index (HHI) for process event distribution.
    Ranges from 1/N (perfectly uniform) to 1.0 (all events by 1 process).
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="process_event_concentration",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_name"],
            mathematical_definition="Sum of squared probabilities of events per process",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"process_event_concentration": float(calculate_hhi(events, "process_name"))}


class ProcessHostDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct hosts per process."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="process_host_diversity",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_name", "host_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT host_name) GROUP BY process_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"process_host_diversity": average_distinct_per_entity(events, "process_name", "host_name")}


class ProcessUserDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct users per process."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="process_user_diversity",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_name", "user_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT user_name) GROUP BY process_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"process_user_diversity": average_distinct_per_entity(events, "process_name", "user_name")}


class ParentChildDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct parent processes per process."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="parent_child_diversity",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_name", "process_parent_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT process_parent_name) GROUP BY process_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"parent_child_diversity": average_distinct_per_entity(events, "process_name", "process_parent_name")}


class CmdlinePatternDiversityFeature(BaseFeature):  # type: ignore[misc]
    """
    Shannon entropy of the NORMALIZED command-line pattern distribution.
    A high entropy indicates that the window contains many structurally different command executions.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="cmdline_pattern_diversity",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_command_line"],
            mathematical_definition="Entropy of normalize_cmdline(process_command_line)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        if not events:
            return {"cmdline_pattern_diversity": 0.0}

        # Create a mock events list with the normalized command lines
        normalized_events = [
            {"normalized_cmd": normalize_cmdline(e.get("process_command_line"))}
            for e in events
        ]

        entropy = calculate_entropy(normalized_events, "normalized_cmd")
        return {"cmdline_pattern_diversity": float(entropy)}


class HistoricalProcessDeviationFeature(BaseFeature):  # type: ignore[misc]
    """
    (Stubbed) Historical frequency of processes against July baseline.
    Returns ratio of events containing unseen processes.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="historical_process_deviation",
            group=FeatureGroup.PROCESSES,
            source_fields=["process_name"],
            mathematical_definition="Ratio of novel events",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Null processes mapped to 'unknown'",
            requires_baseline=True,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        baseline = window_data.get("baseline", {})
        dev = calculate_historical_deviation(events, "process_name", baseline, "known_processes")
        return {"historical_process_deviation": dev}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    ActiveProcessesFeature,
    ProcessEventConcentrationFeature,
    ProcessHostDiversityFeature,
    ProcessUserDiversityFeature,
    ParentChildDiversityFeature,
    CmdlinePatternDiversityFeature,
    HistoricalProcessDeviationFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
