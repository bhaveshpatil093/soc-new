"""
Network-centric behavioral features.

These features capture network-level activity including event volume,
destination and port diversity, protocol usage, and connection concentration.
"""
from __future__ import annotations

from typing import Any

from tads.features.ips import UniqueDestinationIPsFeature
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
)


def _get_connection_tuple(e: dict[str, Any]) -> str:
    """Helper to form a deterministic string representing a network connection."""
    sip = e.get("source_ip") or "unknown"
    dip = e.get("destination_ip") or "unknown"
    dport = e.get("destination_port") or "unknown"
    return f"{sip}:{dip}:{dport}"


class NetworkUniqueDestinationsFeature(UniqueDestinationIPsFeature):  # type: ignore[misc]
    """
    Count of distinct destination_ip values in the window, mapped to the Network group.
    Shares the exact same underlying logic as the IP feature equivalent.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        # Override the metadata to place it in the NETWORK group with a network name.
        meta = super().metadata
        return FeatureMetadata(
            name="network_unique_destinations",
            group=FeatureGroup.NETWORK,
            source_fields=meta.source_fields,
            mathematical_definition=meta.mathematical_definition,
            data_type=meta.data_type,
            expected_range=meta.expected_range,
            missing_value_behavior=meta.missing_value_behavior,
            requires_baseline=meta.requires_baseline,
            is_causal=meta.is_causal,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        # Call the parent logic, but map the result key to this feature's name
        base_result = super().compute(window_data)
        return {"network_unique_destinations": base_result["unique_destination_ips"]}


class UniqueDestinationPortsFeature(BaseFeature):  # type: ignore[misc]
    """Count of distinct destination_port values in the window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="unique_destination_ports",
            group=FeatureGroup.NETWORK,
            source_fields=["destination_port"],
            mathematical_definition="COUNT(DISTINCT destination_port)",
            data_type="int64",
            expected_range=(0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        ports = {e.get("destination_port") or "unknown" for e in events}
        count = len(ports) if events else 0.0
        return {"unique_destination_ports": float(count)}


class SourceDestinationDiversityFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct destination IPs per source IP."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="source_destination_diversity",
            group=FeatureGroup.NETWORK,
            source_fields=["source_ip", "destination_ip"],
            mathematical_definition="MEAN(COUNT(DISTINCT destination_ip) GROUP BY source_ip)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"source_destination_diversity": average_distinct_per_entity(events, "source_ip", "destination_ip")}


class ConnectionConcentrationFeature(BaseFeature):  # type: ignore[misc]
    """Herfindahl-Hirschman Index (HHI) for unique connection tuples (sip:dip:dport)."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="connection_concentration",
            group=FeatureGroup.NETWORK,
            source_fields=["source_ip", "destination_ip", "destination_port"],
            mathematical_definition="Sum of squared probabilities of events per unique connection tuple",
            data_type="float64",
            expected_range=(0.0, 1.0),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        if not events:
            return {"connection_concentration": 0.0}

        mock_events = [{"connection": _get_connection_tuple(e)} for e in events]
        return {"connection_concentration": float(calculate_hhi(mock_events, "connection"))}


class NetworkEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the unique connection tuples (sip:dip:dport)."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="network_entropy",
            group=FeatureGroup.NETWORK,
            source_fields=["source_ip", "destination_ip", "destination_port"],
            mathematical_definition="-Sum(p * log2(p)) across distinct connection tuples",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        if not events:
            return {"network_entropy": 0.0}

        mock_events = [{"connection": _get_connection_tuple(e)} for e in events]
        return {"network_entropy": float(calculate_entropy(mock_events, "connection"))}


class HostNetworkRelationshipsFeature(BaseFeature):  # type: ignore[misc]
    """Average number of distinct connection tuples per host."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_network_relationships",
            group=FeatureGroup.NETWORK,
            source_fields=["host_name", "source_ip", "destination_ip", "destination_port"],
            mathematical_definition="MEAN(COUNT(DISTINCT connection_tuple) GROUP BY host_name)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        if not events:
            return {"host_network_relationships": 0.0}

        mock_events = [{"host_name": e.get("host_name"), "connection": _get_connection_tuple(e)} for e in events]
        return {"host_network_relationships": average_distinct_per_entity(mock_events, "host_name", "connection")}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    NetworkUniqueDestinationsFeature,
    UniqueDestinationPortsFeature,

    SourceDestinationDiversityFeature,
    ConnectionConcentrationFeature,
    NetworkEntropyFeature,
    HostNetworkRelationshipsFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
