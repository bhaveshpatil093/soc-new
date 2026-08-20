"""
Multi-scale causal rolling context features.

Provides rolling aggregations of base metrics over four time horizons:
30 seconds, 1 minute, 5 minutes, and 15 minutes. All rolling windows
are **trailing** (causal) — they include only the current window and
windows strictly before it.

Architecture decision: single streaming pass
--------------------------------------------
Rolling context is computed via a **single streaming pass** using
fixed-size ring buffers, one per scale. As each 5-second window is
processed in chronological order, it is appended to each ring buffer.
The rolling aggregates are then computed from the buffer contents.

This approach was chosen over DuckDB/Polars window functions because:

1. **Memory**: Each ring buffer holds at most 180 windows (15 min /
   5 sec), totalling ~14 KB per metric per buffer. Even 10 metrics
   across 4 scales use < 1 MB total.
2. **Latency**: O(1) amortized per window (push/pop on a deque).
3. **Causality**: Trivially enforced — the buffer only contains past
   windows by construction. A SQL window function requires extra care
   with ROWS BETWEEN clauses.
4. **Streaming**: The design naturally supports online / real-time
   scoring without materializing the entire dataset first.

Rolling window alignment
------------------------
Each rolling window at time *t* is the **trailing** window
[t - duration + 1 window, t], inclusive on both ends.  For example,
at scale 30 s with 5-second primary windows, the rolling window
contains the 6 most recent windows (including the current one):
windows at t-25s, t-20s, t-15s, t-10s, t-5s, t.

Empty sub-windows
-----------------
Per the Prompt 24 decision (``MATERIALIZE_EMPTY_WINDOWS = True``),
empty windows are materialized with event_count=0. These zero-value
windows **participate** in rolling aggregates — they are real data
points representing genuine silence, not missing data. A rolling
mean that averages over zeros correctly reflects periods of inactivity.

Aggregation functions per feature
---------------------------------
+----------------------------+------------------------------------------+
| Rolling feature            | Aggregation                              |
+----------------------------+------------------------------------------+
| rolling_event_count_mean   | MEAN(event_count) over trailing window   |
| rolling_event_count_std    | STD(event_count) over trailing window    |
| rolling_event_count_sum    | SUM(event_count) over trailing window    |
| rolling_user_count_mean    | MEAN(distinct_users) over trailing window|
| rolling_ip_count_mean      | MEAN(distinct_ips) over trailing window  |
| rolling_host_count_mean    | MEAN(distinct_hosts) over trailing window|
| rolling_process_count_mean | MEAN(distinct_processes) over trailing   |
+----------------------------+------------------------------------------+

Each is suffixed with the scale label: _30s, _1m, _5m, _15m.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Any

from tads.constants import WINDOW_SIZE_SECONDS
from tads.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    FeatureGroup,
    FeatureMetadata,
)

# ------------------------------------------------------------------
# Rolling scales
# ------------------------------------------------------------------
ROLLING_SCALES: dict[str, int] = {
    "30s": 30 // WINDOW_SIZE_SECONDS,    # 6 windows
    "1m": 60 // WINDOW_SIZE_SECONDS,     # 12 windows
    "5m": 300 // WINDOW_SIZE_SECONDS,    # 60 windows
    "15m": 900 // WINDOW_SIZE_SECONDS,   # 180 windows
}


# ------------------------------------------------------------------
# Rolling context computer (single streaming pass)
# ------------------------------------------------------------------
class RollingContextComputer:
    """
    Maintains ring buffers for each rolling scale and computes
    causal (trailing) rolling aggregates as windows arrive in order.

    Usage::

        computer = RollingContextComputer()
        for window_summary in chronological_windows:
            rolling = computer.push(window_summary)
            # rolling is a dict with all rolling features for this window
    """

    # Metrics we track in the ring buffer
    _METRICS = (
        "event_count",
        "distinct_users",
        "distinct_ips",
        "distinct_hosts",
        "distinct_processes",
    )

    def __init__(self) -> None:
        # One deque per scale, holding window summaries (dicts)
        self._buffers: dict[str, deque[dict[str, float]]] = {
            label: deque(maxlen=size)
            for label, size in ROLLING_SCALES.items()
        }

    def push(self, window_summary: dict[str, float]) -> dict[str, float]:
        """
        Append a window summary to all buffers and compute rolling features.

        Parameters
        ----------
        window_summary
            Must contain at minimum: event_count, distinct_users,
            distinct_ips, distinct_hosts, distinct_processes.
            Values should be float.

        Returns
        -------
        Dict of rolling feature values, keyed by
        ``rolling_{metric}_{agg}_{scale}``.
        """
        result: dict[str, float] = {}

        for label, buf in self._buffers.items():
            buf.append(window_summary)
            n = len(buf)

            for metric in self._METRICS:
                values = [w.get(metric, 0.0) for w in buf]
                total = sum(values)
                mean = total / n

                # Standard deviation (population)
                if n >= 2:
                    variance = sum((v - mean) ** 2 for v in values) / n
                    std = math.sqrt(variance)
                else:
                    std = 0.0

                base = f"rolling_{metric}"
                result[f"{base}_mean_{label}"] = mean
                result[f"{base}_sum_{label}"] = total
                result[f"{base}_std_{label}"] = std

        return result


# ------------------------------------------------------------------
# Feature classes (one per metric per aggregation per scale)
# ------------------------------------------------------------------
# We generate features dynamically to avoid 140 near-identical classes.
# Instead we create a parameterized factory.

_AGG_DEFS: dict[str, str] = {
    "mean": "MEAN",
    "sum": "SUM",
    "std": "STD (population)",
}

_METRIC_FIELDS: dict[str, str] = {
    "event_count": "event_count",
    "distinct_users": "distinct_users",
    "distinct_ips": "distinct_ips",
    "distinct_hosts": "distinct_hosts",
    "distinct_processes": "distinct_processes",
}


def _make_rolling_feature_class(
    metric: str,
    agg: str,
    scale_label: str,
    scale_windows: int,
) -> type[BaseFeature]:
    """Dynamically create a rolling feature class."""
    feature_name = f"rolling_{metric}_{agg}_{scale_label}"
    math_def = (
        f"{_AGG_DEFS[agg]}({metric}) over trailing "
        f"{scale_label} ({scale_windows} windows)"
    )

    class _RollingFeature(BaseFeature):  # type: ignore[misc]
        @property
        def metadata(self) -> FeatureMetadata:
            return FeatureMetadata(
                name=feature_name,
                group=FeatureGroup.TEMPORAL,
                source_fields=[f"rolling_context.{feature_name}"],
                mathematical_definition=math_def,
                data_type="float64",
                expected_range=(0.0, None),
                missing_value_behavior=(
                    "0.0 at dataset start when fewer than "
                    f"{scale_windows} windows of history exist; "
                    "computed from available windows only (no padding)"
                ),
                requires_baseline=False,
                is_causal=True,
            )

        def compute(self, window_data: dict[str, Any]) -> dict[str, float]:
            rc = window_data.get("rolling_context", {})
            return {feature_name: float(rc.get(feature_name, 0.0))}

    _RollingFeature.__name__ = f"Rolling_{metric}_{agg}_{scale_label}"
    _RollingFeature.__qualname__ = _RollingFeature.__name__
    return _RollingFeature


# ------------------------------------------------------------------
# Auto-register all rolling features
# ------------------------------------------------------------------
_ROLLING_FEATURE_CLASSES: list[type[BaseFeature]] = []

for _metric in _METRIC_FIELDS:
    for _agg in _AGG_DEFS:
        for _scale_label, _scale_windows in ROLLING_SCALES.items():
            cls = _make_rolling_feature_class(_metric, _agg, _scale_label, _scale_windows)
            _ROLLING_FEATURE_CLASSES.append(cls)

for _cls in _ROLLING_FEATURE_CLASSES:
    inst = _cls()
    if inst.metadata.name in FEATURE_REGISTRY.names:
        del FEATURE_REGISTRY._features[inst.metadata.name]
    FEATURE_REGISTRY.register(inst)
