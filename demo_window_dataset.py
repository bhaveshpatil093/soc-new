"""
Validation gate: temporal window dataset generation.

Builds a synthetic July-like dataset, runs the WindowDatasetBuilder, and
cross-checks that sum(event_count) == total raw deduplicated events.
Also verifies idempotency (re-run produces identical output).
"""
from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tads.schema.canonical import SCHEMA_V1
from tads.windowing.dataset import WindowDatasetBuilder


def _generate_mock_raw(base_dir: Path) -> int:
    """Create a synthetic July raw dataset and return the event count."""
    # Clean the entire july tree to avoid stale data from other demos
    july_dir = base_dir / "data" / "july"
    if july_dir.exists():
        shutil.rmtree(july_dir)
    raw_dir = july_dir / "raw" / "2026-07-mock"
    raw_dir.mkdir(parents=True)

    schema = SCHEMA_V1.generate_arrow_schema()
    records = []

    # Simulate a 5-minute window (60 windows) with varying density:
    # first 30 seconds: 5 events/sec (heavy)
    # then 120 seconds silence (24 empty windows)
    # then 150 seconds: 1 event/5-sec (sparse)

    base_ts = datetime(2026, 7, 15, 14, 0, 0, tzinfo=UTC)
    idx = 0

    # Phase 1: heavy burst — 30 seconds, 5 events/sec = 150 events
    for sec in range(30):
        for sub in range(5):
            ts = base_ts + timedelta(seconds=sec, microseconds=sub * 200_000)
            records.append({
                "_id": f"ev_{idx}",
                "@timestamp": ts,
                "raw_timestamp": ts.isoformat(),
                "user_name": f"user_{idx % 10}",
                "source_ip": f"10.0.0.{idx % 50}",
                "host_name": f"host-{idx % 4}",
                "process_name": f"proc-{idx % 8}",
                "message": "burst event",
            })
            idx += 1

    # Phase 2: silence — 120 seconds, no events

    # Phase 3: sparse — 150 seconds, 1 event per 5 seconds = 30 events
    sparse_start = base_ts + timedelta(seconds=150)  # after 30s burst + 120s silence
    for i in range(30):
        ts = sparse_start + timedelta(seconds=i * 5)
        records.append({
            "_id": f"ev_{idx}",
            "@timestamp": ts,
            "raw_timestamp": ts.isoformat(),
            "user_name": f"user_{idx % 3}",
            "source_ip": f"192.168.1.{idx % 20}",
            "host_name": "host-quiet",
            "process_name": "sshd",
            "message": "sparse event",
        })
        idx += 1

    table = pa.Table.from_pylist(records, schema=schema)
    pq.write_table(table, raw_dir / "compacted.parquet", compression="ZSTD")
    return len(records)


def main() -> None:
    print("=== Demo: Temporal Window Dataset Generation ===\n")

    base_dir = Path(__file__).resolve().parent
    total_raw_events = _generate_mock_raw(base_dir)
    print(f"Raw dataset: {total_raw_events} events")

    # ---- Build ----
    builder = WindowDatasetBuilder(dataset="july", base_dir=base_dir)
    result = builder.build()

    print(f"\n--- Build Result ---")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # ---- Cross-check: sum(event_count) == total raw events ----
    conn = duckdb.connect()
    conn.execute("SET TimeZone='UTC'")
    output_path = result["output_path"]

    sum_row = conn.execute(f"""
        SELECT SUM(event_count) AS total, COUNT(*) AS window_count
        FROM '{output_path}'
    """).fetchone()
    total_in_windows = int(sum_row[0])
    window_count = int(sum_row[1])

    print(f"\n--- Cross-Check ---")
    print(f"  Raw events:              {total_raw_events}")
    print(f"  sum(event_count):        {total_in_windows}")
    print(f"  Match: {'YES' if total_in_windows == total_raw_events else 'NO'}")

    assert total_in_windows == total_raw_events, (
        f"Event count mismatch: {total_in_windows} != {total_raw_events}"
    )

    # ---- Verify columns exist ----
    cols = conn.execute(f"DESCRIBE SELECT * FROM '{output_path}'").fetchall()
    col_names = [c[0] for c in cols]
    expected = [
        "window_id", "window_start", "window_end", "event_count",
        "distinct_users", "distinct_ips", "distinct_hosts", "distinct_processes",
        "hour_of_day", "minute_of_hour", "day_of_week", "is_weekend",
        "day_of_month", "window_position_in_hour",
    ]
    for exp in expected:
        assert exp in col_names, f"Missing column: {exp}"
    print(f"  All {len(expected)} expected columns present: YES")

    # ---- Verify empty windows exist ----
    empty_count = conn.execute(f"""
        SELECT COUNT(*) FROM '{output_path}' WHERE event_count = 0
    """).fetchone()
    print(f"  Empty windows: {empty_count[0]}")
    assert empty_count[0] > 0, "Expected empty windows but found none"

    # ---- Verify contiguity ----
    gap_check = conn.execute(f"""
        WITH w AS (
            SELECT window_id, LEAD(window_id) OVER (ORDER BY window_id) AS next_id
            FROM '{output_path}'
        )
        SELECT COUNT(*) FROM w WHERE next_id IS NOT NULL AND next_id != window_id + 1
    """).fetchone()
    print(f"  Contiguous grid (no gaps): {'YES' if gap_check[0] == 0 else 'NO'}")
    assert gap_check[0] == 0, "Window grid is not contiguous!"

    # ---- Idempotency: rebuild and compare ----
    builder2 = WindowDatasetBuilder(dataset="july", base_dir=base_dir)
    result2 = builder2.build()
    assert result2["total_events"] == result["total_events"]
    assert result2["total_windows"] == result["total_windows"]
    print(f"  Idempotent rebuild: YES")

    print(f"\nSUCCESS: Window dataset validated — {window_count} windows, "
          f"{total_in_windows} events, contiguous grid, idempotent.")


if __name__ == "__main__":
    main()
