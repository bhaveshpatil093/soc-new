"""
Logic to group consecutive or related anomalous 5-second windows into anomaly episodes.

This reduces alert fatigue and provides holistic context for multi-window attacks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from datetime import datetime

    import pyarrow as pa


@dataclass
class AnomalyEpisode:
    """A collection of related anomalous windows grouped in time."""
    episode_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    window_count: int
    peak_evidence: float
    mean_evidence: float
    affected_users: set[str] = field(default_factory=set)
    affected_ips: set[str] = field(default_factory=set)
    affected_hosts: set[str] = field(default_factory=set)
    affected_processes: set[str] = field(default_factory=set)
    model_agreement_mean: float = 0.0
    primary_categories: set[str] = field(default_factory=set)
    evidence_trend: list[float] = field(default_factory=list)


class EpisodeGrouper:
    """
    Groups anomalous windows into episodes based on configurable temporal bounds
    and evidence thresholds.
    """
    def __init__(
        self,
        evidence_floor: float = 0.90,
        max_gap_seconds: float = 15.0,
        alert_threshold: float = 0.95,
    ) -> None:
        """
        Args:
            evidence_floor: Windows above this evidence are eligible to be grouped.
                (Default 0.90 represents 10% FPR background noise floor)
            max_gap_seconds: Maximum time allowed between two windows above the floor
                before the episode is split. (Default 15s allows 2 intervening windows).
            alert_threshold: The peak evidence of the episode MUST reach this value
                for the episode to be emitted.
        """
        self.evidence_floor = evidence_floor
        self.max_gap_seconds = max_gap_seconds
        self.alert_threshold = alert_threshold

    def group(self, data: pa.Table) -> list[AnomalyEpisode]:
        """
        Group rows from the combined window/evidence table into episodes.

        Assumes `data` contains:
        - `window_start`: timestamp
        - `ensemble_evidence`: float
        - `detector_agreement`: int
        - `primary_category`: str
        - optionally: `user`, `host`, `source_ip`, `dest_ip`, `process_name`

        And assumes `data` is sorted chronologically.
        """
        if len(data) == 0:
            return []

        timestamps = data.column("window_start").to_pylist()
        evidence = data.column("ensemble_evidence").to_numpy()
        agreements = data.column("detector_agreement").to_numpy()
        categories = data.column("primary_category").to_pylist()

        # Extract optional entity sets if present
        def get_col(name: str) -> list[str]:
            if name in data.column_names:
                # Convert nulls to empty string or handle them gracefully
                return [str(v) if v is not None else "" for v in data.column(name).to_pylist()]
            return [""] * len(data)

        users = get_col("user")
        hosts = get_col("host")
        src_ips = get_col("source_ip")
        dst_ips = get_col("dest_ip")
        processes = get_col("process_name")

        episodes: list[AnomalyEpisode] = []
        current_window_indices: list[int] = []

        def finalize_episode() -> None:
            if not current_window_indices:
                return

            peak_ev = float(np.max(evidence[current_window_indices]))

            # Episode only triggers if it crosses the strict alerting threshold
            if peak_ev >= self.alert_threshold:
                start_ts = timestamps[current_window_indices[0]]
                end_ts = timestamps[current_window_indices[-1]]
                duration = (end_ts - start_ts).total_seconds()

                ep = AnomalyEpisode(
                    episode_id=f"EP-{uuid.uuid4().hex[:8]}",
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_seconds=duration,
                    window_count=len(current_window_indices),
                    peak_evidence=peak_ev,
                    mean_evidence=float(np.mean(evidence[current_window_indices])),
                    model_agreement_mean=float(np.mean(agreements[current_window_indices])),
                    affected_users={users[i] for i in current_window_indices if users[i]},
                    affected_hosts={hosts[i] for i in current_window_indices if hosts[i]},
                    affected_ips={src_ips[i] for i in current_window_indices if src_ips[i]} |
                                 {dst_ips[i] for i in current_window_indices if dst_ips[i]},
                    affected_processes={processes[i] for i in current_window_indices if processes[i]},
                    primary_categories={categories[i] for i in current_window_indices if categories[i]},
                    evidence_trend=[float(ev) for ev in evidence[current_window_indices]],
                )
                episodes.append(ep)

            current_window_indices.clear()

        for i in range(len(data)):
            ev = evidence[i]
            ts = timestamps[i]

            if ev >= self.evidence_floor:
                if current_window_indices:
                    last_ts = timestamps[current_window_indices[-1]]
                    gap = (ts - last_ts).total_seconds()

                    if gap > self.max_gap_seconds:
                        finalize_episode()

                current_window_indices.append(i)

        finalize_episode()
        return episodes
