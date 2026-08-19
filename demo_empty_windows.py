"""
Validation gate: empty window materialization.

Simulates an overnight quiet period with sparse events to demonstrate that
empty windows are correctly materialized, round-trip without vanishing or
being double-counted, and form a contiguous time grid.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import shutil

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tads.constants import WINDOW_SIZE_MS
from tads.windowing.empty_windows import materialize_empty_windows

_WINDOW_SECS = WINDOW_SIZE_MS // 1000


def main() -> None:
    print("=== Demo: Empty Window Materialization ===\n")

    base = Path(__file__).resolve().parent / "data" / "_demo_empty"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    # ------------------------------------------------------------------
    # 1. Simulate a 10-minute overnight period (120 × 5-second windows)
    #    with only 5 sparse event bursts.
    # ------------------------------------------------------------------
    t0 = datetime(2026, 8, 2, 3, 0, 0, tzinfo=UTC)  # 03:00 UTC — quiet time
    event_offsets_sec = [0, 15, 60, 180, 595]  # seconds into the 10-min span

    sparse_ids: list[int] = []
    for off in event_offsets_sec:
        ts = t0 + timedelta(seconds=off)
        epoch_ms = int(ts.timestamp() * 1000)
        wid = epoch_ms // WINDOW_SIZE_MS
        if wid not in sparse_ids:
            sparse_ids.append(wid)

    # Build a sparse window_summary with only those windows
    rows = []
    for wid in sparse_ids:
        rows.append({
            "window_id": wid,
            "window_start": datetime.fromtimestamp(wid * _WINDOW_SECS, tz=UTC),
            "window_end": datetime.fromtimestamp(wid * _WINDOW_SECS + _WINDOW_SECS, tz=UTC),
            "event_count": 3,
        })
    schema = pa.schema([
        pa.field("window_id", pa.int64()),
        pa.field("window_start", pa.timestamp("us", tz="UTC")),
        pa.field("window_end", pa.timestamp("us", tz="UTC")),
        pa.field("event_count", pa.int64()),
    ])
    sparse_path = base / "window_summary_sparse.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), sparse_path, compression="ZSTD")

    total_span = max(sparse_ids) - min(sparse_ids) + 1
    print(f"Sparse summary: {len(sparse_ids)} non-empty windows out of a span of {total_span}")
    print(f"Expected empty windows to add: {total_span - len(sparse_ids)}\n")

    # ------------------------------------------------------------------
    # 2. Materialize
    # ------------------------------------------------------------------
    dense_path = base / "window_summary_dense.parquet"
    result = materialize_empty_windows(sparse_path, dense_path)

    print("--- Materialization Result ---")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # ------------------------------------------------------------------
    # 3. Verify: contiguous grid, no duplicates, correct counts
    # ------------------------------------------------------------------
    conn = duckdb.connect()
    conn.execute("SET TimeZone='UTC'")

    dense_rows = conn.execute(f"""
        SELECT window_id, event_count
        FROM '{dense_path}'
        ORDER BY window_id
    """).fetchall()

    ids = [r[0] for r in dense_rows]
    counts = [r[1] for r in dense_rows]

    # Contiguity check
    for i in range(1, len(ids)):
        assert ids[i] == ids[i - 1] + 1, f"Gap at index {i}: {ids[i - 1]} -> {ids[i]}"

    # No duplicates
    assert len(ids) == len(set(ids)), "Duplicate window_ids detected!"

    # Total event count preserved
    non_empty = [c for c in counts if c > 0]
    empty = [c for c in counts if c == 0]
    assert sum(non_empty) == len(sparse_ids) * 3
    assert len(non_empty) == len(sparse_ids)

    print(f"\n--- Verification ---")
    print(f"  Total windows in dense grid: {len(ids)}")
    print(f"  Non-empty windows: {len(non_empty)}")
    print(f"  Empty windows: {len(empty)}")
    print(f"  Contiguous: YES (no gaps)")
    print(f"  Duplicates: NONE")
    print(f"  Total events preserved: {sum(non_empty)}")

    # ------------------------------------------------------------------
    # 4. Round-trip: re-materialize, should be idempotent
    # ------------------------------------------------------------------
    rt_path = base / "window_summary_rt.parquet"
    rt_result = materialize_empty_windows(dense_path, rt_path)
    assert rt_result["empty_windows_added"] == 0, "Round-trip added spurious windows!"
    assert rt_result["total_windows"] == result["total_windows"]

    rt_rows = conn.execute(f"""
        SELECT window_id, event_count FROM '{rt_path}' ORDER BY window_id
    """).fetchall()
    assert rt_rows == dense_rows, "Round-trip changed data!"

    print(f"  Round-trip idempotent: YES (0 windows added on 2nd pass)\n")
    print("SUCCESS: Empty windows materialized, contiguous, no duplicates, idempotent round-trip.")


if __name__ == "__main__":
    main()
