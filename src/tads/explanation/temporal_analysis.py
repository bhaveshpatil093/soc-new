"""
Classifies anomaly episodes into temporal behavior patterns.

Categorizes episodes as Occurring Once, Repeating, Persisting, Escalating,
or Recurring Periodically based entirely on their temporal metrics and
entity overlap, without using static attack signatures.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from tads.explanation.episodes import AnomalyEpisode


class TemporalAnalyzer:
    """Analyzes a collection of episodes to determine their temporal behavior."""

    def __init__(
        self,
        persist_threshold_seconds: float = 60.0,
        escalation_correlation_threshold: float = 0.8,
        periodicity_cv_threshold: float = 0.1,
    ) -> None:
        self.persist_threshold_seconds = persist_threshold_seconds
        self.escalation_correlation_threshold = escalation_correlation_threshold
        self.periodicity_cv_threshold = periodicity_cv_threshold

    def analyze(self, episodes: list[AnomalyEpisode]) -> dict[str, list[AnomalyEpisode]]:
        """
        Evaluate episodes and return a mapping of temporal category to matching episodes.
        """
        results: dict[str, list[AnomalyEpisode]] = {
            "occur once": [],
            "repeat": [],
            "persist": [],
            "escalate": [],
            "recur periodically": [],
        }

        # Sort chronologically for sequence analysis
        episodes = sorted(episodes, key=lambda e: e.start_time)

        # 1. Map entities to episodes to find repeats
        entity_to_episodes: dict[str, list[AnomalyEpisode]] = defaultdict(list)
        for ep in episodes:
            entities = ep.affected_users | ep.affected_ips | ep.affected_hosts
            if not entities:
                # If an episode has no identifiable entities, give it a synthetic key
                # so it is treated as "occur once" unless another identical empty one appears?
                # Usually we only track overlaps of known entities.
                pass
            for ent in entities:
                entity_to_episodes[ent].append(ep)

        # Group episodes into sets of "repeats" (connected components)
        # For simplicity, we define a repeat sequence by exactly matching the primary entity.
        # We will iterate through all entity sequences that have >= 2 episodes.
        repeat_sequences = [seq for seq in entity_to_episodes.values() if len(seq) >= 2]
        repeated_episode_ids = {ep.episode_id for seq in repeat_sequences for ep in seq}

        for ep in episodes:
            # Occur Once vs Repeat
            if ep.episode_id in repeated_episode_ids:
                results["repeat"].append(ep)
            else:
                results["occur once"].append(ep)

            # Persist
            if ep.duration_seconds >= self.persist_threshold_seconds:
                results["persist"].append(ep)

            # Intra-Episode Escalation
            # Need at least 4 windows to calculate a meaningful trend
            if len(ep.evidence_trend) >= 4:
                # Spearman rank correlation to detect monotonic upward trend
                n = len(ep.evidence_trend)
                time_ranks = np.arange(n)
                # Handle edge cases where variance is zero
                if np.std(ep.evidence_trend) > 1e-6:
                    correlation = float(np.corrcoef(time_ranks, ep.evidence_trend)[0, 1])
                    if correlation >= self.escalation_correlation_threshold:
                        results["escalate"].append(ep)

        # Sequence-level analysis (Inter-episode escalation and Periodicity)
        for seq in repeat_sequences:
            # They are already sorted by time because we appended them in order

            # Inter-Episode Escalation (Strictly increasing peak evidence across 3+ episodes)
            if len(seq) >= 3:
                peaks = [ep.peak_evidence for ep in seq]
                is_escalating = all(peaks[i] < peaks[i+1] for i in range(len(peaks)-1))
                if is_escalating:
                    for ep in seq:
                        if ep not in results["escalate"]:
                            results["escalate"].append(ep)

            # Periodicity (Consistent time deltas)
            if len(seq) >= 3:
                deltas = [(seq[i+1].start_time - seq[i].start_time).total_seconds() for i in range(len(seq)-1)]
                mean_delta = float(np.mean(deltas))
                std_delta = float(np.std(deltas))
                if mean_delta > 0:
                    cv = std_delta / mean_delta
                    if cv <= self.periodicity_cv_threshold:
                        for ep in seq:
                            if ep not in results["recur periodically"]:
                                results["recur periodically"].append(ep)

        return results
