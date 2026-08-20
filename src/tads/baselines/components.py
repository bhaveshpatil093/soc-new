"""
Implementation of Baseline Categories for the persistent July baseline system.

These components learn historical facts (e.g., seen users, seen IPs) exclusively from July data.
"""

from __future__ import annotations

from typing import Any

import pyarrow as pa

from tads.baselines.base import BaseBaseline


class DistributionBaseline(BaseBaseline):  # type: ignore[misc]
    """
    Generic baseline that tracks distinct values of a specific field (e.g., users, IPs, hosts).
    Stores results in self.state["known_entities"].
    """
    def __init__(self, field_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.field_name = field_name
        self.state["known_entities"] = set()

    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        if isinstance(data, pa.Table):
            if self.field_name in data.column_names:
                unique_vals = set(data.column(self.field_name).to_pylist())
                # filter out None
                unique_vals = {v for v in unique_vals if v is not None}
                self.state["known_entities"].update(unique_vals)
        else:
            for row in data:
                val = row.get(self.field_name)
                if val is not None:
                    self.state["known_entities"].add(val)


    def to_dict(self) -> dict[str, Any]:
        return {"known_entities": list(self.state["known_entities"])}

    def from_dict(self, data: dict[str, Any]) -> None:
        self.state["known_entities"] = set(data.get("known_entities", []))


class GlobalDistributionBaseline(DistributionBaseline):
    """Tracks global events or categories (e.g. event_category)."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(field_name="event_category", **kwargs)

class UserDistributionBaseline(DistributionBaseline):
    """Tracks known users."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(field_name="user_name", **kwargs)

class IpDistributionBaseline(DistributionBaseline):
    """Tracks known IPs."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(field_name="source_ip", **kwargs)

class HostDistributionBaseline(DistributionBaseline):
    """Tracks known hosts."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(field_name="host_name", **kwargs)

class ProcessDistributionBaseline(DistributionBaseline):
    """Tracks known processes."""
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(field_name="process_name", **kwargs)

class RelationshipFrequencyBaseline(BaseBaseline):  # type: ignore[misc]
    """Tracks known pairs of entities (e.g., user to host)."""

    def __init__(self, field_1: str, field_2: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.field_1 = field_1
        self.field_2 = field_2
        self.state["known_pairs"] = set()

    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        if isinstance(data, pa.Table):
            if self.field_1 in data.column_names and self.field_2 in data.column_names:
                col1 = data.column(self.field_1).to_pylist()
                col2 = data.column(self.field_2).to_pylist()
                for v1, v2 in zip(col1, col2, strict=False):
                    if v1 is not None and v2 is not None:
                        self.state["known_pairs"].add((v1, v2))
        else:
            for row in data:
                v1 = row.get(self.field_1)
                v2 = row.get(self.field_2)
                if v1 is not None and v2 is not None:
                    self.state["known_pairs"].add((v1, v2))

    def to_dict(self) -> dict[str, Any]:
        return {"known_pairs": [list(pair) for pair in self.state["known_pairs"]]}

    def from_dict(self, data: dict[str, Any]) -> None:
        self.state["known_pairs"] = set(tuple(pair) for pair in data.get("known_pairs", []))


# Note: FeatureStatisticsBaseline has been replaced by RobustFeatureStatisticsBaseline in statistics.py


class TemporalStatisticsBaseline(BaseBaseline):  # type: ignore[misc]
    """Tracks temporal distributions, such as event rates by hour."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # map hour (0-23) to count of events
        self.state["events_per_hour"] = {h: 0 for h in range(24)}

    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        if isinstance(data, pa.Table):
            if "hour_of_day" in data.column_names:
                hours = data.column("hour_of_day").to_pylist()
                for h in hours:
                    if h is not None and 0 <= h < 24:
                        self.state["events_per_hour"][int(h)] += 1
        else:
            for row in data:
                h = row.get("hour_of_day")
                if h is not None and 0 <= h < 24:
                    self.state["events_per_hour"][int(h)] += 1

    def to_dict(self) -> dict[str, Any]:
        return {"events_per_hour": {str(k): v for k, v in self.state["events_per_hour"].items()}}

    def from_dict(self, data: dict[str, Any]) -> None:
        raw = data.get("events_per_hour", {})
        self.state["events_per_hour"] = {int(k): v for k, v in raw.items()}
