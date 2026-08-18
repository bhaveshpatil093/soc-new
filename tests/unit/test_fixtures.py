"""
Test: Synthetic data fixture validation

Verifies that the test fixtures generate correct, reproducible synthetic data.
These tests validate the test infrastructure itself.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from tests.conftest import generate_synthetic_events


class TestSyntheticDataGeneration:
    """Verify synthetic data generators produce valid data."""

    def test_generates_correct_count(self) -> None:
        """Generated table has the requested number of rows."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table = generate_synthetic_events(n_events=100, base_timestamp=base_ts, seed=42)
        assert table.num_rows == 100

    def test_has_required_columns(self) -> None:
        """Generated table includes all expected columns."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table = generate_synthetic_events(n_events=10, base_timestamp=base_ts, seed=42)
        expected_columns = {
            "@timestamp", "source_ip", "dest_ip", "dest_port",
            "protocol", "action", "bytes_sent", "bytes_received",
            "user_agent", "event_type",
        }
        assert set(table.column_names) == expected_columns

    def test_timestamps_within_range(self) -> None:
        """All timestamps fall within [base, base + duration]."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        duration = 60.0
        table = generate_synthetic_events(
            n_events=100, base_timestamp=base_ts,
            duration_seconds=duration, seed=42,
        )
        ts_column = table.column("@timestamp")
        end_ts = base_ts + datetime.timedelta(seconds=duration)

        for ts in ts_column.to_pylist():
            assert ts >= base_ts, f"Timestamp {ts} before base {base_ts}"
            assert ts <= end_ts, f"Timestamp {ts} after end {end_ts}"

    def test_timestamps_are_sorted(self) -> None:
        """Generated timestamps are in ascending order."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table = generate_synthetic_events(n_events=100, base_timestamp=base_ts, seed=42)
        timestamps = table.column("@timestamp").to_pylist()
        assert timestamps == sorted(timestamps)

    def test_reproducibility_same_seed(self) -> None:
        """Same seed produces identical output (Constraint #20)."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table1 = generate_synthetic_events(n_events=50, base_timestamp=base_ts, seed=123)
        table2 = generate_synthetic_events(n_events=50, base_timestamp=base_ts, seed=123)
        assert table1.equals(table2)

    def test_different_seed_different_output(self) -> None:
        """Different seeds produce different output."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table1 = generate_synthetic_events(n_events=50, base_timestamp=base_ts, seed=1)
        table2 = generate_synthetic_events(n_events=50, base_timestamp=base_ts, seed=2)
        assert not table1.equals(table2)

    def test_returns_pyarrow_table(self) -> None:
        """Generator returns a PyArrow Table, not a pandas DataFrame."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table = generate_synthetic_events(n_events=10, base_timestamp=base_ts, seed=42)
        assert isinstance(table, pa.Table)

    def test_parquet_roundtrip(self, tmp_data_dir: Path) -> None:
        """Generated data survives a Parquet write/read roundtrip."""
        base_ts = datetime.datetime(2025, 7, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        table = generate_synthetic_events(n_events=100, base_timestamp=base_ts, seed=42)

        path = tmp_data_dir / "roundtrip_test.parquet"
        pq.write_table(table, path, compression="zstd")

        loaded = pq.read_table(path)
        assert loaded.num_rows == table.num_rows
        assert loaded.column_names == table.column_names
