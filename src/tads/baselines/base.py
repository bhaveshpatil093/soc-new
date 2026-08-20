"""
Base classes and exceptions for the persistent July baseline system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc

from tads.models.base import TemporalLeakageError

if TYPE_CHECKING:
    from pathlib import Path


class ImmutableBaselineError(Exception):
    """Raised when an operation attempts to modify a frozen baseline."""


def _get_max_timestamp(data: pa.Table | list[dict[str, Any]], timestamp_col: str) -> datetime | None:
    """Extract the maximum timestamp from either a PyArrow table or a list of dicts."""
    if isinstance(data, pa.Table):
        if timestamp_col not in data.column_names:
            raise ValueError(f"Data must contain a '{timestamp_col}' column for temporal validation.")
        if len(data) == 0:
            return None
        max_ts = pc.max(data.column(timestamp_col)).as_py()
        if isinstance(max_ts, int):
            # Convert epoch ms to datetime
            max_ts = datetime.fromtimestamp(max_ts / 1000.0, tz=UTC)
        return max_ts

    if isinstance(data, list):
        if not data:
            return None
        max_ts_val = max((row.get(timestamp_col, 0) for row in data if row.get(timestamp_col) is not None), default=None)
        if max_ts_val is None:
            return None
        if isinstance(max_ts_val, (int, float)):
             # Assuming epoch milliseconds
             return datetime.fromtimestamp(max_ts_val / 1000.0, tz=UTC)
        if isinstance(max_ts_val, datetime):
            return max_ts_val
        raise TypeError(f"Unexpected timestamp type: {type(max_ts_val)}")

    raise TypeError("Data must be a pyarrow.Table or a list of dictionaries.")


def validate_baseline_temporal_bounds(
    data: pa.Table | list[dict[str, Any]],
    max_allowed_timestamp: datetime,
    timestamp_col: str = "window_start",
) -> None:
    """
    Validates that no data in the baseline training set exceeds the maximum allowed timestamp.
    Enforces the 'Strict Train/Test Separation' principle (No August data in training).
    """
    max_ts = _get_max_timestamp(data, timestamp_col)

    if max_ts is None:
        return

    if max_ts.tzinfo is None:
        max_ts = max_ts.replace(tzinfo=UTC)

    if max_allowed_timestamp.tzinfo is None:
        max_allowed_timestamp = max_allowed_timestamp.replace(tzinfo=UTC)

    if max_ts >= max_allowed_timestamp:
        raise TemporalLeakageError(
            f"Temporal leakage detected! Found baseline data with timestamp {max_ts}, "
            f"which is >= the maximum allowed training bound of {max_allowed_timestamp}."
        )


class BaseBaseline(ABC):
    """
    Base class for baseline components.

    Enforces immutability and temporal leakage checks.
    """

    def __init__(self, training_end_bound: datetime | None = None) -> None:
        self.is_frozen = False
        # Default bound: August 1st, 2025 UTC
        self.training_end_bound = training_end_bound or datetime(2025, 8, 1, tzinfo=UTC)
        self.state: dict[str, Any] = {}

    def fit(self, data: pa.Table | list[dict[str, Any]], timestamp_col: str = "window_start") -> None:
        """
        Fit the baseline to the provided data.

        Raises ImmutableBaselineError if the baseline is frozen.
        Raises TemporalLeakageError if data exceeds the July boundary.
        """
        if self.is_frozen:
            raise ImmutableBaselineError("Cannot fit a frozen baseline.")

        validate_baseline_temporal_bounds(data, self.training_end_bound, timestamp_col=timestamp_col)
        self._fit(data)

    @abstractmethod
    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        """Internal fit implementation to be overridden by subclasses."""
        pass

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for storage (default JSON serialization)."""
        return self.state

    def from_dict(self, data: dict[str, Any]) -> None:
        """Deserialize state from storage (default JSON serialization)."""
        self.state = data

    def save(self, version_dir: Path, name: str) -> None:
        """Save the baseline state to the version directory."""
        import json
        state_file = version_dir / f"{name}.json"
        state_file.write_text(json.dumps(self.to_dict(), indent=2))

    def load(self, version_dir: Path, name: str) -> None:
        """Load the baseline state from the version directory."""
        import json
        state_file = version_dir / f"{name}.json"
        if state_file.exists():
            raw_state = json.loads(state_file.read_text())
            self.from_dict(raw_state)

