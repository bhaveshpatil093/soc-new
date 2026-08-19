"""
IP-centric behavioral features.

These features capture network-level activity including IP diversity,
concentration, internal/external routing proportions, and baseline IP
frequency / relationship novelty.
"""
from __future__ import annotations

import ipaddress
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
    calculate_relationship_novelty,
)

# Configurable definition of internal networks.
# Users can override this list at runtime to redefine "internal".
INTERNAL_SUBNETS_CONFIG: list[str] = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",  # Loopback
]


def _is_internal(ip_str: str | None) -> bool:
    """Check if an IP string belongs to any of the configured internal subnets."""
    if not ip_str:
        return False
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return any(ip_obj in ipaddress.ip_network(subnet_str) for subnet_str in INTERNAL_SUBNETS_CONFIG)
    except ValueError:
        return False


class UniqueSourceIPsFeature(BaseFeature):  # type: ignore[misc]
    """Count of distinct source_ip values in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="unique_source_ips",
            group=FeatureGroup.IPS,
            source_fields=["source_ip"],
            mathematical_definition="COUNT(DISTINCT source_ip)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        ips = {e.get("source_ip") or "unknown" for e in events}
        count = len(ips) if events else 0.0
        return {"unique_source_ips": float(count)}


class UniqueDestinationIPsFeature(BaseFeature):  # type: ignore[misc]
    """Count of distinct destination_ip values in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="unique_destination_ips",
            group=FeatureGroup.IPS,
            source_fields=["destination_ip"],
            mathematical_definition="COUNT(DISTINCT destination_ip)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        ips = {e.get("destination_ip") or "unknown" for e in events}
        count = len(ips) if events else 0.0
        return {"unique_destination_ips": float(count)}


class SourceIpConcentrationFeature(BaseFeature):  # type: ignore[misc]
    """
    Herfindahl-Hirschman Index (HHI) for source IP distribution.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="source_ip_concentration",
            group=FeatureGroup.IPS,
            source_fields=["source_ip"],
            mathematical_definition="Sum of squared probabilities of events per source_ip",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"source_ip_concentration": float(calculate_hhi(events, "source_ip"))}


class DestinationDiversityFeature(BaseFeature):  # type: ignore[misc]
    """
    Shannon entropy of the destination IP event distribution.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="destination_diversity",
            group=FeatureGroup.IPS,
            source_fields=["destination_ip"],
            mathematical_definition="-Sum(p * log2(p)) across distinct destination_ips",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"destination_diversity": float(calculate_entropy(events, "destination_ip"))}


class InternalExternalProportionFeature(BaseFeature):  # type: ignore[misc]
    """
    Proportion of source IPs that are internal vs external.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="internal_source_ratio",
            group=FeatureGroup.IPS,
            source_fields=["source_ip"],
            mathematical_definition="Internal Source IPs / Total Source IPs (ignoring null/invalid)",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls/invalid excluded from total",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        total_valid = 0
        internal_count = 0

        for e in events:
            ip = e.get("source_ip")
            if not ip:
                continue

            # Check if it's a valid IP string (don't count gibberish in denominator)
            try:
                ipaddress.ip_address(ip)
                total_valid += 1
                if _is_internal(ip):
                    internal_count += 1
            except ValueError:
                pass

        ratio = (internal_count / total_valid) if total_valid > 0 else 0.0
        return {"internal_source_ratio": float(ratio)}


class IpUserDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct users per source IP."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="ip_user_diversity",
            group=FeatureGroup.IPS,
            source_fields=["source_ip", "user_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT user_name) GROUP BY source_ip)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"ip_user_diversity": average_distinct_per_entity(events, "source_ip", "user_name")}


class IpHostDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct hosts per source IP."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="ip_host_diversity",
            group=FeatureGroup.IPS,
            source_fields=["source_ip", "host_name"],
            mathematical_definition="MEAN(COUNT(DISTINCT host_name) GROUP BY source_ip)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"ip_host_diversity": average_distinct_per_entity(events, "source_ip", "host_name")}


class HistoricalIpFrequencyFeature(BaseFeature):  # type: ignore[misc]
    """
    (Stubbed) Historical frequency of source IPs against July baseline.
    Returns 1.0 for completely unseen IPs (maximally novel), and 0.0 for fully baseline IPs.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="historical_ip_deviation",
            group=FeatureGroup.IPS,
            source_fields=["source_ip"],
            mathematical_definition="Stubbed baseline comparison. Novel IPs -> 1.0.",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Null IPs mapped to 'unknown'",
            requires_baseline=True,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        baseline = window_data.get("baseline", {})
        dev = calculate_historical_deviation(events, "source_ip", baseline, "known_source_ips")
        return {"historical_ip_deviation": dev}


class RelationshipNoveltyFeature(BaseFeature):  # type: ignore[misc]
    """
    (Stubbed) Checks if the specific (source_ip, user_name) pair was seen in July.
    Returns ratio of events containing novel relationships.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="relationship_novelty_ip_user",
            group=FeatureGroup.RELATIONSHIP_NOVELTY,
            source_fields=["source_ip", "user_name"],
            mathematical_definition="Ratio of events with unseen (source_ip, user_name) pairs.",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=True,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        baseline = window_data.get("baseline", {})
        ratio = calculate_relationship_novelty(events, "source_ip", "user_name", baseline, "known_ip_user_pairs")
        return {"relationship_novelty_ip_user": ratio}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    UniqueSourceIPsFeature,
    UniqueDestinationIPsFeature,
    SourceIpConcentrationFeature,
    DestinationDiversityFeature,
    InternalExternalProportionFeature,
    IpUserDiversityFeature,
    IpHostDiversityFeature,
    HistoricalIpFrequencyFeature,
    RelationshipNoveltyFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
