"""
Defensible event attribution logic.

Maps window-level feature deviations back to the specific raw events that
plausibly drove them. Avoids unjustified causal attribution for global/statistical
anomalies, but aggressively isolates categorical/novelty anomalies.
"""

import re
from dataclasses import dataclass
from typing import Any

import tads.features.hosts
import tads.features.ips
import tads.features.users
import tads.features.volume  # noqa
from tads.features.registry import FEATURE_REGISTRY


@dataclass
class AttributedEvent:
    """Record of a raw event that contributed to a window anomaly."""
    event_id: str
    timestamp: str
    relevant_fields: dict[str, Any]
    anomalous_features: list[str]
    attribution_method: str
    attribution_confidence: str


class EventAttributor:
    """
    Traces anomalous features to raw events defensibly.
    """

    def __init__(self) -> None:
        pass

    def attribute(
        self,
        raw_events: list[dict[str, Any]],
        anomalous_feature_strings: list[str],
    ) -> list[AttributedEvent]:
        """
        Identify which raw events drove the specified features.

        Args:
            raw_events: All events occurring in the anomalous window.
            anomalous_feature_strings: Descriptions of the anomalies, e.g.,
                "user='eve'", "f_latency", "event_count".
                These usually come from detector .explain() outputs.

        Returns:
            A list of attributed events explaining the deviations.
        """
        attributed: dict[str, AttributedEvent] = {}

        for feat_str in anomalous_feature_strings:
            self._process_feature(feat_str, raw_events, attributed)

        # Sort by timestamp
        sorted_events = sorted(
            attributed.values(),
            key=lambda e: e.timestamp
        )
        return sorted_events

    def _process_feature(
        self,
        feat_str: str,
        raw_events: list[dict[str, Any]],
        attributed: dict[str, AttributedEvent],
    ) -> None:
        """Process a single anomalous feature string and update the attributed dict."""
        # 1. Check for categorical exact match (e.g., user='eve')
        match = re.search(r"(\w+)='([^']+)'", feat_str)
        if match:
            field, value = match.groups()
            self._attribute_exact_match(field, value, feat_str, raw_events, attributed)
            return

        # 2. Check for registered feature definitions to do subset matching
        feature_name = feat_str.split()[0] # e.g. "f_latency" or "authentication_volume"
        if feature_name in FEATURE_REGISTRY.names:
            metadata = FEATURE_REGISTRY.get(feature_name).metadata

            # Simple heuristic for subset features based on metadata name
            if "authentication" in feature_name.lower():
                self._attribute_subset_match(
                    "event_category", "authentication", metadata.source_fields, feature_name, raw_events, attributed
                )
                return
            if "network" in feature_name.lower():
                self._attribute_subset_match(
                    "event_category", "network", metadata.source_fields, feature_name, raw_events, attributed
                )
                return

            # If it's just a general volume or math feature, it's a global distribution
            self._attribute_global_distribution(feature_name, metadata.source_fields, raw_events, attributed)
            return

        # 3. Fallback: Global distribution for unknown/unregistered features
        # e.g., f_latency, f_cpu mock features which aren't in the registry
        fallback_fields = [feature_name.replace("f_", "")]
        self._attribute_global_distribution(feature_name, fallback_fields, raw_events, attributed)

    def _attribute_exact_match(
        self,
        field: str,
        value: str,
        feature_name: str,
        raw_events: list[dict[str, Any]],
        attributed: dict[str, AttributedEvent],
    ) -> None:
        """Exact match filtering for categorical novelty."""
        method = "Exact Match Filter"
        confidence = "HIGH (Exact Match)"
        relevant_fields = [field]

        for ev in raw_events:
            if str(ev.get(field, "")) == value:
                self._add_or_update(
                    ev, relevant_fields, feature_name, method, confidence, attributed
                )

    def _attribute_subset_match(
        self,
        filter_field: str,
        filter_value: str,
        source_fields: list[str],
        feature_name: str,
        raw_events: list[dict[str, Any]],
        attributed: dict[str, AttributedEvent],
    ) -> None:
        """Subset filtering (e.g. for unique counts or specific volume types)."""
        method = "Subset Filter"
        confidence = "HIGH (Subset Match)"

        for ev in raw_events:
            if str(ev.get(filter_field, "")).lower() == filter_value.lower():
                self._add_or_update(
                    ev, source_fields, feature_name, method, confidence, attributed
                )

    def _attribute_global_distribution(
        self,
        feature_name: str,
        source_fields: list[str],
        raw_events: list[dict[str, Any]],
        attributed: dict[str, AttributedEvent],
    ) -> None:
        """Global attribution when the feature is a property of the entire window."""
        method = "Global Distribution"
        confidence = "MEDIUM (Window Distribution)"

        # To be defensible, we don't attribute a 10,000 event volume anomaly to a single event.
        # We attribute it to all events in the window (or a sampled subset to avoid memory explosion).
        # We'll cap the returned events at 100 for global distributions.
        max_events = 100

        for i, ev in enumerate(raw_events):
            if i >= max_events:
                break
            self._add_or_update(
                ev, source_fields, feature_name, method, confidence, attributed
            )

    def _add_or_update(
        self,
        ev: dict[str, Any],
        relevant_field_names: list[str],
        feature_name: str,
        method: str,
        confidence: str,
        attributed: dict[str, AttributedEvent],
    ) -> None:
        """Helper to create or append to an AttributedEvent."""
        event_id = str(ev.get("_id", ev.get("id", id(ev))))
        timestamp = str(ev.get("@timestamp", ev.get("timestamp", "unknown")))

        # Extract only relevant fields, avoiding dumping entire PII payloads
        relevant_fields_data = {
            k: ev.get(k) for k in relevant_field_names if k in ev
        }

        if event_id in attributed:
            existing = attributed[event_id]
            if feature_name not in existing.anomalous_features:
                existing.anomalous_features.append(feature_name)
            existing.relevant_fields.update(relevant_fields_data)
            # Downgrade confidence if multiple methods apply (e.g. EXACT + GLOBAL = MEDIUM)
            if existing.attribution_confidence != confidence and "MEDIUM" in confidence:
                existing.attribution_confidence = confidence
                existing.attribution_method = f"{existing.attribution_method} + {method}"
        else:
            attributed[event_id] = AttributedEvent(
                event_id=event_id,
                timestamp=timestamp,
                relevant_fields=relevant_fields_data,
                anomalous_features=[feature_name],
                attribution_method=method,
                attribution_confidence=confidence,
            )
