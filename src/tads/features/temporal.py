"""
Causal temporal features.

These features capture temporal dynamics by comparing the current window
to its immediately preceding window(s). Every feature here is strictly
causal — it only reads data from the current window and windows before it
in time.

Design contract
---------------
The ``window_data`` dict must contain:

- ``"events"``: list of event dicts in the current window
- ``"previous_window"``: a dict with summary metrics from the immediately
  preceding 5-second window (or ``None`` / absent if this is the first
  window). Expected keys:
    - ``event_count`` (float)
    - ``distinct_users`` (float)
    - ``distinct_ips`` (float)
    - ``distinct_hosts`` (float)
    - ``distinct_processes`` (float)

When ``previous_window`` is absent or ``None``, change-based features
return ``0.0`` (no change observable).

Burstiness metric
-----------------
We use the **Fano factor** (variance / mean of inter-event times) rather
than the coefficient of variation (CV).  Rationale:

1. The Fano factor is defined for Poisson processes (F = 1), providing a
   natural baseline: F > 1 = bursty, F < 1 = regular, F = 1 = Poisson.
2. CV requires sigma / mu, which is undefined when mu = 0 (single event or
   empty window). The Fano factor has the same issue but is more commonly
   handled with a "return 0" convention.
3. The Fano factor is widely used in spike-train analysis and network
   traffic burstiness studies.
"""
from __future__ import annotations

from typing import Any

from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
_WINDOW_SECONDS = 5.0


def _get_previous(window_data: dict[str, Any]) -> dict[str, float] | None:
    """Safely retrieve the previous-window summary dict."""
    prev = window_data.get("previous_window")
    if prev is None:
        return None
    return prev


def _inter_event_times(events: list[dict[str, Any]]) -> list[float]:
    """
    Compute sorted inter-arrival times (in seconds) from event timestamps.

    Expects each event dict to have a ``"@timestamp"`` key holding a
    numeric value (epoch milliseconds).  Events missing the field are
    silently skipped.
    """
    timestamps = sorted(
        e["@timestamp"]
        for e in events
        if e.get("@timestamp") is not None
    )
    if len(timestamps) < 2:
        return []
    return [(timestamps[i + 1] - timestamps[i]) / 1000.0 for i in range(len(timestamps) - 1)]


# ------------------------------------------------------------------
# Feature implementations
# ------------------------------------------------------------------


class PreviousWindowEventCountFeature(BaseFeature):  # type: ignore[misc]
    """Event count of the immediately preceding window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="previous_window_event_count",
            group=FeatureGroup.TEMPORAL,
            source_fields=["previous_window.event_count"],
            mathematical_definition="event_count(window_{t-1})",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="0.0 if no previous window exists",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        prev = _get_previous(window_data)
        if prev is None:
            return {"previous_window_event_count": 0.0}
        return {"previous_window_event_count": float(prev.get("event_count", 0))}


class EventRateChangeFeature(BaseFeature):  # type: ignore[misc]
    """Absolute change in event count vs the previous window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="event_rate_change",
            group=FeatureGroup.TEMPORAL,
            source_fields=["events", "previous_window.event_count"],
            mathematical_definition="event_count(t) - event_count(t-1)",
            data_type="float64",
            expected_range=(None, None),
            missing_value_behavior="0.0 if no previous window",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        current_count = float(len(window_data.get("events", [])))
        prev = _get_previous(window_data)
        if prev is None:
            return {"event_rate_change": 0.0}
        prev_count = float(prev.get("event_count", 0))
        return {"event_rate_change": current_count - prev_count}


class UserCountChangeFeature(BaseFeature):  # type: ignore[misc]
    """Absolute change in distinct user count vs the previous window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="user_count_change",
            group=FeatureGroup.TEMPORAL,
            source_fields=["user_name", "previous_window.distinct_users"],
            mathematical_definition="distinct_users(t) - distinct_users(t-1)",
            data_type="float64",
            expected_range=(None, None),
            missing_value_behavior="0.0 if no previous window",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        current = float(len({e.get("user_name") or "unknown" for e in events})) if events else 0.0
        prev = _get_previous(window_data)
        if prev is None:
            return {"user_count_change": 0.0}
        return {"user_count_change": current - float(prev.get("distinct_users", 0))}


class IpCountChangeFeature(BaseFeature):  # type: ignore[misc]
    """Absolute change in distinct source IP count vs the previous window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="ip_count_change",
            group=FeatureGroup.TEMPORAL,
            source_fields=["source_ip", "previous_window.distinct_ips"],
            mathematical_definition="distinct_source_ips(t) - distinct_source_ips(t-1)",
            data_type="float64",
            expected_range=(None, None),
            missing_value_behavior="0.0 if no previous window",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        current = float(len({e.get("source_ip") or "unknown" for e in events})) if events else 0.0
        prev = _get_previous(window_data)
        if prev is None:
            return {"ip_count_change": 0.0}
        return {"ip_count_change": current - float(prev.get("distinct_ips", 0))}


class HostCountChangeFeature(BaseFeature):  # type: ignore[misc]
    """Absolute change in distinct host count vs the previous window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="host_count_change",
            group=FeatureGroup.TEMPORAL,
            source_fields=["host_name", "previous_window.distinct_hosts"],
            mathematical_definition="distinct_hosts(t) - distinct_hosts(t-1)",
            data_type="float64",
            expected_range=(None, None),
            missing_value_behavior="0.0 if no previous window",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        current = float(len({e.get("host_name") or "unknown" for e in events})) if events else 0.0
        prev = _get_previous(window_data)
        if prev is None:
            return {"host_count_change": 0.0}
        return {"host_count_change": current - float(prev.get("distinct_hosts", 0))}


class ProcessCountChangeFeature(BaseFeature):  # type: ignore[misc]
    """Absolute change in distinct process count vs the previous window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="process_count_change",
            group=FeatureGroup.TEMPORAL,
            source_fields=["process_name", "previous_window.distinct_processes"],
            mathematical_definition="distinct_processes(t) - distinct_processes(t-1)",
            data_type="float64",
            expected_range=(None, None),
            missing_value_behavior="0.0 if no previous window",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        events = window_data.get("events", [])
        current = float(len({e.get("process_name") or "unknown" for e in events})) if events else 0.0
        prev = _get_previous(window_data)
        if prev is None:
            return {"process_count_change": 0.0}
        return {"process_count_change": current - float(prev.get("distinct_processes", 0))}


class InterEventMeanFeature(BaseFeature):  # type: ignore[misc]
    """Mean inter-arrival time (seconds) within the current window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="inter_event_mean",
            group=FeatureGroup.TEMPORAL,
            source_fields=["@timestamp"],
            mathematical_definition="MEAN(inter-arrival times in seconds)",
            data_type="float64",
            expected_range=(0.0, _WINDOW_SECONDS),
            missing_value_behavior="0.0 if fewer than 2 events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        iets = _inter_event_times(window_data.get("events", []))
        if not iets:
            return {"inter_event_mean": 0.0}
        return {"inter_event_mean": sum(iets) / len(iets)}


class InterEventVarianceFeature(BaseFeature):  # type: ignore[misc]
    """Variance of inter-arrival times (seconds²) within the current window."""

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="inter_event_variance",
            group=FeatureGroup.TEMPORAL,
            source_fields=["@timestamp"],
            mathematical_definition="VAR(inter-arrival times in seconds)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="0.0 if fewer than 2 events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        iets = _inter_event_times(window_data.get("events", []))
        if not iets:
            return {"inter_event_variance": 0.0}
        mean = sum(iets) / len(iets)
        variance = sum((x - mean) ** 2 for x in iets) / len(iets)
        return {"inter_event_variance": variance}


class BurstinessFeature(BaseFeature):  # type: ignore[misc]
    """
    Fano factor of inter-event times within the current window.

    F = variance / mean.  F > 1 indicates bursty arrivals, F < 1 indicates
    regular arrivals, F ≈ 1 indicates Poisson-like arrivals.

    Returns 0.0 when fewer than 2 events (mean undefined).
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="burstiness",
            group=FeatureGroup.TEMPORAL,
            source_fields=["@timestamp"],
            mathematical_definition="Fano factor: VAR(IET) / MEAN(IET)",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="0.0 if fewer than 2 events",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        iets = _inter_event_times(window_data.get("events", []))
        if not iets:
            return {"burstiness": 0.0}
        mean = sum(iets) / len(iets)
        if mean == 0.0:
            # All events at the exact same timestamp -> perfectly bursty
            return {"burstiness": 0.0}
        variance = sum((x - mean) ** 2 for x in iets) / len(iets)
        return {"burstiness": variance / mean}


class TimeSincePreviousActivityFeature(BaseFeature):  # type: ignore[misc]
    """
    Time gap (in seconds) between the last event in the previous window
    and the first event in the current window.

    This captures periods of silence between windows. If either window
    has no events, returns the full 5-second window duration as the gap.
    """

    @property
    def metadata(self) -> FeatureMetadata:
        return FeatureMetadata(
            name="time_since_previous_activity",
            group=FeatureGroup.TEMPORAL,
            source_fields=["@timestamp", "previous_window.last_event_ts"],
            mathematical_definition="first_event_ts(t) - last_event_ts(t-1), in seconds",
            data_type="float64",
            expected_range=(0.0, None),
            missing_value_behavior="5.0 if either window has no timestamp data",
            requires_baseline=False,
            is_causal=True,
        )

    def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
        prev = _get_previous(window_data)
        if prev is None:
            return {"time_since_previous_activity": _WINDOW_SECONDS}

        prev_last_ts = prev.get("last_event_ts")
        if prev_last_ts is None:
            return {"time_since_previous_activity": _WINDOW_SECONDS}

        events = window_data.get("events", [])
        timestamps = sorted(
            e["@timestamp"]
            for e in events
            if e.get("@timestamp") is not None
        )
        if not timestamps:
            return {"time_since_previous_activity": _WINDOW_SECONDS}

        gap = (timestamps[0] - prev_last_ts) / 1000.0
        return {"time_since_previous_activity": max(0.0, gap)}


# ------------------------------------------------------------------
# Auto-register
# ------------------------------------------------------------------
_FEATURES: list[type[BaseFeature]] = [
    PreviousWindowEventCountFeature,
    EventRateChangeFeature,
    UserCountChangeFeature,
    IpCountChangeFeature,
    HostCountChangeFeature,
    ProcessCountChangeFeature,
    InterEventMeanFeature,
    InterEventVarianceFeature,
    BurstinessFeature,
    TimeSincePreviousActivityFeature,
]

for _cls in _FEATURES:
    if _cls().metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[_cls().metadata.name]
    FEATURE_REGISTRY.register(_cls())
