"""
Entropy-centric behavioral features.

These features calculate the Shannon entropy for appropriate categorical
distributions. They capture the diversity and spread of activity across
various entities (users, IPs, hosts, processes, etc.).
"""
from __future__ import annotations

from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)
from tads.features.utils import calculate_entropy


class UserEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the user event distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_entropy",
            group=FeatureGroup.ENTROPY,
            source_fields=["user_name"],
            mathematical_definition="-Sum(p * log2(p)) across distinct users",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"user_entropy": float(calculate_entropy(events, "user_name"))}


class IpEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the source IP event distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="source_ip_entropy",
            group=FeatureGroup.ENTROPY,
            source_fields=["source_ip"],
            mathematical_definition="-Sum(p * log2(p)) across distinct source_ips",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"source_ip_entropy": float(calculate_entropy(events, "source_ip"))}


class HostEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the host event distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_entropy",
            group=FeatureGroup.ENTROPY,
            source_fields=["host_name"],
            mathematical_definition="-Sum(p * log2(p)) across distinct hosts",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"host_entropy": float(calculate_entropy(events, "host_name"))}


class ProcessEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the process event distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="process_entropy",
            group=FeatureGroup.ENTROPY,
            source_fields=["process_name"],
            mathematical_definition="-Sum(p * log2(p)) across distinct processes",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"process_entropy": float(calculate_entropy(events, "process_name"))}


class DestinationEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the destination IP event distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="destination_entropy",
            group=FeatureGroup.ENTROPY,
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
        return {"destination_entropy": float(calculate_entropy(events, "destination_ip"))}


class ProtocolEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the network protocol distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="protocol_entropy",
            group=FeatureGroup.ENTROPY,
            source_fields=["network_protocol"],
            mathematical_definition="-Sum(p * log2(p)) across distinct network_protocols",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"protocol_entropy": float(calculate_entropy(events, "network_protocol"))}


class CategoryEntropyFeature(BaseFeature):  # type: ignore[misc]
    """Shannon entropy of the event category distribution."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="event_category_entropy",
            group=FeatureGroup.ENTROPY,
            source_fields=["event_category"],
            mathematical_definition="-Sum(p * log2(p)) across distinct event categories",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="Nulls mapped to 'unknown'",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        return {"event_category_entropy": float(calculate_entropy(events, "event_category"))}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    UserEntropyFeature,
    IpEntropyFeature,
    HostEntropyFeature,
    ProcessEntropyFeature,
    DestinationEntropyFeature,
    ProtocolEntropyFeature,
    CategoryEntropyFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
