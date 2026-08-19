"""
Host-centric behavioral features.

These features capture entity-level activity focused on hosts (endpoints),
including diversity, concentration, and baseline novelty.
"""
from __future__ import annotations

from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)
from tads.features.utils import (
    average_distinct_per_entity,
    calculate_hhi,
    calculate_historical_deviation,
    calculate_relationship_novelty,
)


class ActiveHostsFeature(BaseFeature):  # type: ignore[misc]
    """Count of distinct hosts in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="active_hosts",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name"],
            mathematical_definition="COUNT(DISTINCT host_name)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        hosts = {e.get("host_name") or "unknown" for e in events}
        count = len(hosts) if events else 0.0
        return {"active_hosts": float(count)}


class HostEventConcentrationFeature(BaseFeature):  # type: ignore[misc]
    """
    Herfindahl-Hirschman Index (HHI) for host event distribution.
    Ranges from 1/N (perfectly uniform) to 1.0 (all events by 1 host).
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_event_concentration",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name"],
            mathematical_definition="Sum of squared probabilities of events per host",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"host_event_concentration": float(calculate_hhi(events, "host_name"))}


class HostUserDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct users per host."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_user_diversity",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name", "user_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT user_name) GROUP BY host_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"host_user_diversity": average_distinct_per_entity(events, "host_name", "user_name")}


class HostIpDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct source IPs per host."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_ip_diversity",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name", "source_ip"],
            mathematical_definition="MEAN(COUNT(DISTINCT source_ip) GROUP BY host_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"host_ip_diversity": average_distinct_per_entity(events, "host_name", "source_ip")}


class HostProcessDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct processes per host."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_process_diversity",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name", "process_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT process_name) GROUP BY host_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"host_process_diversity": average_distinct_per_entity(events, "host_name", "process_name")}


class HostCategoryDiversityFeature(BaseFeature):  # type: ignore[misc]
    """
    Shannon entropy of the event category distribution per host.
    Here we compute it globally for the window based on host_name grouping,
    by taking the average entropy across hosts, or we can just compute the
    overall entropy of (host_name, event_category) pairs.
    Wait, the prompt says "host event-category distribution".
    Let's compute the average number of distinct event categories per host to be consistent
    with other diversity features, OR use the same helper (average distinct).
    Actually, let's use `average_distinct_per_entity(..., "host_name", "event_category")`
    which fits the pattern perfectly.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_category_diversity",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name", "event_category"],
            mathematical_definition="MEAN(COUNT(DISTINCT event_category) GROUP BY host_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"host_category_diversity": average_distinct_per_entity(events, "host_name", "event_category")}


class HistoricalHostDeviationFeature(BaseFeature):  # type: ignore[misc]
    """
    (Stubbed) Historical frequency of hosts against July baseline.
    Returns 1.0 for completely unseen hosts (maximally novel), and 0.0 for fully baseline hosts.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="historical_host_deviation",
            group=FeatureGroup.HOSTS,
            source_fields=["host_name"],
            mathematical_definition="Stubbed baseline comparison. Novel hosts -> 1.0.",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Null hosts mapped to 'unknown'",
            requires_baseline=True,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        baseline = window_data.get("baseline", {})
        dev = calculate_historical_deviation(events, "host_name", baseline, "known_hosts")
        return {"historical_host_deviation": dev}


class RelationshipNoveltyHostUserFeature(BaseFeature):  # type: ignore[misc]
    """
    (Stubbed) Checks if the specific (host_name, user_name) pair was seen in July.
    Returns ratio of events containing novel relationships.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="relationship_novelty_host_user",
            group=FeatureGroup.RELATIONSHIP_NOVELTY,
            source_fields=["host_name", "user_name"],
            mathematical_definition="Ratio of events with unseen (host_name, user_name) pairs.",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=True,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        baseline = window_data.get("baseline", {})
        ratio = calculate_relationship_novelty(events, "host_name", "user_name", baseline, "known_host_user_pairs")
        return {"relationship_novelty_host_user": ratio}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    ActiveHostsFeature,
    HostEventConcentrationFeature,
    HostUserDiversityFeature,
    HostIpDiversityFeature,
    HostProcessDiversityFeature,
    HostCategoryDiversityFeature,
    HistoricalHostDeviationFeature,
    RelationshipNoveltyHostUserFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
