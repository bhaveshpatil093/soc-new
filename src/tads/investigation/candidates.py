"""
Investigation pipeline to identify model-only candidate anomalies.

Filters out anomalies that are already covered by legacy monitoring alerts.
Strict terminology enforcement is applied: outputs are always referred to as
"model-only candidate anomalies", never "attacks" or "threats".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from tads.explanation.attribution import EventAttributor
from tads.explanation.episodes import AnomalyEpisode
from tads.explanation.temporal_analysis import TemporalAnalyzer


@dataclass
class LegacyAlert:
    """Mock schema for an existing Elastic/Kibana alert."""
    alert_id: str
    rule_name: str
    timestamp: datetime
    entities: set[str] = field(default_factory=set)


@dataclass
class ModelOnlyCandidate:
    """
    A model-only candidate anomaly.

    This represents an episode of statistically unusual behaviour that
    was NOT flagged by any legacy monitoring alert.
    """
    episode: AnomalyEpisode
    attribution_data: dict[str, Any]
    temporal_context: list[str]  # e.g., ["persist", "escalate"]
    drift_context: list[str]
    alert_clearance_statement: str = (
        "CONFIRMED: No matching existing legacy alert was found in the comparison window."
    )


class AlertCrossReferencer:
    """Cross-references episodes against legacy alerts to find model-only candidates."""

    def __init__(self, time_window_minutes: float = 5.0):
        self.time_window = timedelta(minutes=time_window_minutes)

    def cross_reference(
        self,
        episodes: list[AnomalyEpisode],
        legacy_alerts: list[LegacyAlert],
        attributor: EventAttributor,
        temporal_analyzer: TemporalAnalyzer,
        drift_context_map: dict[str, str],
        raw_events: Any = None,
    ) -> list[ModelOnlyCandidate]:
        """
        Identify episodes that are completely unseen by legacy alerts.
        """
        # 1. Gather temporal categories
        temporal_classifications = temporal_analyzer.analyze(episodes)
        ep_to_temporal = {ep.episode_id: [] for ep in episodes}
        for category, eps in temporal_classifications.items():
            for ep in eps:
                ep_to_temporal[ep.episode_id].append(category)

        candidates = []

        for ep in episodes:
            # Check for legacy alert overlap
            is_covered = False
            ep_entities = ep.affected_users | ep.affected_hosts | ep.affected_ips
            
            # The search window spans the episode duration +/- the buffer
            search_start = ep.start_time - self.time_window
            search_end = ep.end_time + self.time_window

            for alert in legacy_alerts:
                # 1. Temporal overlap
                if search_start <= alert.timestamp <= search_end:
                    # 2. Entity overlap
                    if not alert.entities.isdisjoint(ep_entities):
                        is_covered = True
                        break

            if not is_covered:
                # It is a Model-Only Candidate Anomaly
                
                # We would run attribution here. In a real system `raw_events` is a pa.Table
                # containing the events that fall into this episode's time bounds.
                # For this mock, we just stub attribution if no raw_events are provided.
                if raw_events is not None:
                    # For this mock, we just stub the attribution with a count.
                    # In reality raw_events is a list of dicts.
                    attribution_summary = {"mock_attribution": "Stubbed (Raw events provided)"}
                else:
                    attribution_summary = {"mock_attribution": "Stubbed"}

                # Gather drift context for the features implicated in this episode
                # In a real system, we'd map primary_categories -> features -> drift.
                # Here we just pass the global drift map for now.
                ep_drift = [
                    f"{feat}: {status}"
                    for feat, status in drift_context_map.items()
                    if "No Drift" not in status
                ]

                candidate = ModelOnlyCandidate(
                    episode=ep,
                    attribution_data=attribution_summary,
                    temporal_context=ep_to_temporal[ep.episode_id],
                    drift_context=ep_drift,
                )
                candidates.append(candidate)

        return candidates
