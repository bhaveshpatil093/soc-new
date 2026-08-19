"""Tests for empty window materialization."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tads.constants import WINDOW_SIZE_MS
from tads.windowing.empty_windows import materialize_empty_windows

_WINDOW_SECS = WINDOW_SIZE_MS // 1000


def _make_sparse_summary(tmp_path: Path, window_ids: list[int]) -> Path:
    """Write a minimal window_summary.parquet with only the given window_ids."""
    rows = []
    for wid in window_ids:
        rows.append({
            "window_id": wid,
            "window_start": datetime.fromtimestamp(wid * _WINDOW_SECS, tz=UTC),
            "window_end": datetime.fromtimestamp(wid * _WINDOW_SECS + _WINDOW_SECS, tz=UTC),
            "event_count": 10,
        })
    schema = pa.schema([
        pa.field("window_id", pa.int64()),
        pa.field("window_start", pa.timestamp("us", tz="UTC")),
        pa.field("window_end", pa.timestamp("us", tz="UTC")),
        pa.field("event_count", pa.int64()),
    ])
    table = pa.Table.from_pylist(rows, schema=schema)
    path = tmp_path / "window_summary.parquet"
    pq.write_table(table, path, compression="ZSTD")
    return path


class TestEmptyWindowMaterialization:

    def test_fills_gaps(self, tmp_path: Path) -> None:
        """Gaps between existing window_ids are filled with event_count=0."""
        # window_ids 100, 103 → gap at 101, 102
        src = _make_sparse_summary(tmp_path, [100, 103])
        out = tmp_path / "dense.parquet"

        result = materialize_empty_windows(src, out)

        assert result["total_windows"] == 4
        assert result["non_empty_windows"] == 2
        assert result["empty_windows_added"] == 2

        conn = duckdb.connect()
        conn.execute("SET TimeZone='UTC'")
        rows = conn.execute(f"""
            SELECT window_id, event_count
            FROM '{out}'
            ORDER BY window_id
        """).fetchall()

        assert len(rows) == 4
        assert rows[0] == (100, 10)
        assert rows[1] == (101, 0)
        assert rows[2] == (102, 0)
        assert rows[3] == (103, 10)

    def test_no_gaps_is_noop(self, tmp_path: Path) -> None:
        """Contiguous window_ids produce no empty windows."""
        src = _make_sparse_summary(tmp_path, [200, 201, 202])
        out = tmp_path / "dense.parquet"

        result = materialize_empty_windows(src, out)

        assert result["total_windows"] == 3
        assert result["empty_windows_added"] == 0

    def test_single_window(self, tmp_path: Path) -> None:
        """A single window produces exactly one row, zero added."""
        src = _make_sparse_summary(tmp_path, [500])
        out = tmp_path / "dense.parquet"

        result = materialize_empty_windows(src, out)

        assert result["total_windows"] == 1
        assert result["empty_windows_added"] == 0

    def test_round_trip_preserves_count(self, tmp_path: Path) -> None:
        """Running materialization twice on the same file is idempotent."""
        src = _make_sparse_summary(tmp_path, [10, 15])
        out = tmp_path / "dense.parquet"

        r1 = materialize_empty_windows(src, out)
        assert r1["total_windows"] == 6
        assert r1["empty_windows_added"] == 4

        # Run again on the dense output
        out2 = tmp_path / "dense2.parquet"
        r2 = materialize_empty_windows(out, out2)
        assert r2["total_windows"] == 6
        assert r2["empty_windows_added"] == 0  # already dense

    def test_empty_windows_have_correct_timestamps(self, tmp_path: Path) -> None:
        """Materialized empty windows have mathematically correct start/end."""
        src = _make_sparse_summary(tmp_path, [100, 103])
        out = tmp_path / "dense.parquet"
        materialize_empty_windows(src, out)

        conn = duckdb.connect()
        conn.execute("SET TimeZone='UTC'")
        rows = conn.execute(f"""
            SELECT window_id, window_start, window_end, event_count
            FROM '{out}'
            WHERE event_count = 0
            ORDER BY window_id
        """).fetchall()

        for wid, ws, we, ec in rows:
            expected_start = datetime.fromtimestamp(wid * _WINDOW_SECS, tz=UTC)
            expected_end = datetime.fromtimestamp(wid * _WINDOW_SECS + _WINDOW_SECS, tz=UTC)
            assert ws == expected_start
            assert we == expected_end
            assert ec == 0
