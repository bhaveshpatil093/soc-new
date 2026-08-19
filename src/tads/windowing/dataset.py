"""
Temporal window dataset builder.

Transforms canonical Parquet events (post-normalization, post-dedup) into a
5-second window dataset where each row represents one temporal window.

Columns produced
----------------
window_id            int64   — deterministic integer id (epoch_ms // 5000)
window_start         timestamp(us, UTC)
window_end           timestamp(us, UTC)
event_count          int64
distinct_users       int64   — unique user_name values in the window
distinct_ips         int64   — unique source_ip values
distinct_hosts       int64   — unique host_name values
distinct_processes   int64   — unique process_name values
hour_of_day          int32   — 0-23
minute_of_hour       int32   — 0-59
day_of_week          int32   — 0 (Mon) - 6 (Sun)
is_weekend           bool
day_of_month         int32   — 1-31
window_position_in_hour  int32 — which 5-sec slot within the hour (0-719)

The pipeline is:
  1. Scan raw compacted.parquet files with DuckDB.
  2. GROUP BY window_id, computing cardinalities and temporal metadata.
  3. If MATERIALIZE_EMPTY_WINDOWS is True, fill gaps with zero-count rows.
  4. Write output to data/<dataset>/windows/ partitioned by date.

Re-running on a fixed raw dataset is deterministic and idempotent.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import duckdb

from tads.constants import (
    MATERIALIZE_EMPTY_WINDOWS,
    WINDOW_SIZE_MS,
    WINDOW_SIZE_SECONDS,
)

logger = logging.getLogger(__name__)

_WINDOW_SECS = WINDOW_SIZE_SECONDS


class WindowDatasetBuilder:
    """Builds the 5-second window dataset from canonical Parquet events."""

    def __init__(self, dataset: str, base_dir: Path | str | None = None) -> None:
        assert dataset in ("july", "august"), "Invalid dataset namespace"
        self.dataset = dataset

        if base_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.base_dir = project_root
        else:
            self.base_dir = Path(base_dir)

        self.raw_dir = self.base_dir / "data" / dataset / "raw"
        self.window_dir = self.base_dir / "data" / dataset / "windows"

    def build(self) -> dict[str, int | str]:
        """Execute the full window dataset pipeline.

        Returns a dict with build metrics.
        """
        import glob

        pattern = str(self.raw_dir / "*" / "compacted.parquet")
        if not glob.glob(pattern):
            logger.warning("No compacted parquet files found for %s", self.dataset)
            return {"status": "no_data"}

        # Clean previous output for idempotency
        if self.window_dir.exists():
            shutil.rmtree(self.window_dir)
        self.window_dir.mkdir(parents=True)

        conn = duckdb.connect(database=":memory:")
        conn.execute("SET TimeZone='UTC'")

        try:
            # ---- Step 1: Build per-window aggregates ----
            # CTE computes window_id per event; outer query groups by it.
            window_query = f"""
                CREATE TABLE window_dataset AS
                WITH events AS (
                    SELECT
                        *,
                        CAST(FLOOR((epoch("@timestamp") * 1000) / {WINDOW_SIZE_MS})
                             AS BIGINT) AS window_id
                    FROM '{pattern}'
                )
                SELECT
                    window_id,
                    to_timestamp(window_id * {_WINDOW_SECS}) AS window_start,
                    to_timestamp(window_id * {_WINDOW_SECS} + {_WINDOW_SECS}) AS window_end,
                    COUNT(*) AS event_count,
                    COUNT(DISTINCT user_name) AS distinct_users,
                    COUNT(DISTINCT source_ip) AS distinct_ips,
                    COUNT(DISTINCT host_name) AS distinct_hosts,
                    COUNT(DISTINCT process_name) AS distinct_processes,
                    CAST(EXTRACT(HOUR FROM
                        to_timestamp(window_id * {_WINDOW_SECS})) AS INTEGER) AS hour_of_day,
                    CAST(EXTRACT(MINUTE FROM
                        to_timestamp(window_id * {_WINDOW_SECS})) AS INTEGER) AS minute_of_hour,
                    CAST(EXTRACT(DOW FROM
                        to_timestamp(window_id * {_WINDOW_SECS})) AS INTEGER) AS day_of_week,
                    EXTRACT(DOW FROM
                        to_timestamp(window_id * {_WINDOW_SECS})) IN (0, 6) AS is_weekend,
                    CAST(EXTRACT(DAY FROM
                        to_timestamp(window_id * {_WINDOW_SECS})) AS INTEGER) AS day_of_month,
                    CAST(
                        (EXTRACT(HOUR FROM to_timestamp(window_id * {_WINDOW_SECS})) * 720 +
                         EXTRACT(MINUTE FROM to_timestamp(window_id * {_WINDOW_SECS})) * 12 +
                         EXTRACT(SECOND FROM to_timestamp(window_id * {_WINDOW_SECS}))
                            / {_WINDOW_SECS})
                    AS INTEGER) AS window_position_in_hour
                FROM events
                GROUP BY window_id
                ORDER BY window_id
            """
            conn.execute(window_query)

            # Get stats before empty-fill
            stats = conn.execute("""
                SELECT COUNT(*) AS n, SUM(event_count) AS total_events
                FROM window_dataset
            """).fetchone()
            non_empty_windows = int(stats[0]) if stats else 0
            total_events = int(stats[1]) if stats and stats[1] else 0

            # ---- Step 2: Write to a single file first ----
            summary_path = self.window_dir / "window_dataset.parquet"
            conn.execute(f"""
                COPY (SELECT * FROM window_dataset ORDER BY window_id)
                TO '{summary_path}' (FORMAT PARQUET, CODEC 'ZSTD')
            """)

            # ---- Step 3: Materialize empty windows if configured ----
            empty_added = 0
            if MATERIALIZE_EMPTY_WINDOWS and non_empty_windows > 0:
                # We need a window_summary-compatible file for the fill function
                # The fill function only cares about window_id and event_count;
                # we do a custom fill here that preserves our extra columns.
                empty_result = self._fill_empty_windows(conn, summary_path)
                empty_added = empty_result.get("empty_windows_added", 0)

            # Get final count
            final_stats = conn.execute(f"""
                SELECT COUNT(*) FROM '{summary_path}'
            """).fetchone()
            final_window_count = int(final_stats[0]) if final_stats else 0

            return {
                "status": "success",
                "dataset": self.dataset,
                "non_empty_windows": non_empty_windows,
                "empty_windows_added": empty_added,
                "total_windows": final_window_count,
                "total_events": total_events,
                "output_path": str(summary_path),
            }
        finally:
            conn.close()

    def _fill_empty_windows(
        self, conn: duckdb.DuckDBPyConnection, summary_path: Path
    ) -> dict[str, int]:
        """Fill gaps in the window dataset with zero-count rows."""
        tmp_path = summary_path.with_suffix(".tmp.parquet")

        stats = conn.execute(f"""
            SELECT MIN(window_id) AS lo, MAX(window_id) AS hi, COUNT(*) AS n
            FROM '{summary_path}'
        """).fetchone()

        if stats is None or stats[0] is None:
            return {"empty_windows_added": 0}

        lo, hi, existing = int(stats[0]), int(stats[1]), int(stats[2])
        total_span = hi - lo + 1

        if total_span == existing:
            return {"empty_windows_added": 0}

        conn.execute(f"""
            CREATE OR REPLACE TABLE all_ids AS
            SELECT CAST({lo} + i AS BIGINT) AS window_id
            FROM generate_series(0, {total_span - 1}) AS t(i)
        """)

        conn.execute(f"""
            COPY (
                SELECT
                    a.window_id,
                    COALESCE(w.window_start,
                        to_timestamp(a.window_id * {_WINDOW_SECS})) AS window_start,
                    COALESCE(w.window_end,
                        to_timestamp(a.window_id * {_WINDOW_SECS} + {_WINDOW_SECS})) AS window_end,
                    COALESCE(w.event_count, 0) AS event_count,
                    COALESCE(w.distinct_users, 0) AS distinct_users,
                    COALESCE(w.distinct_ips, 0) AS distinct_ips,
                    COALESCE(w.distinct_hosts, 0) AS distinct_hosts,
                    COALESCE(w.distinct_processes, 0) AS distinct_processes,
                    COALESCE(w.hour_of_day,
                        CAST(EXTRACT(HOUR FROM
                            to_timestamp(a.window_id * {_WINDOW_SECS})) AS INTEGER)
                    ) AS hour_of_day,
                    COALESCE(w.minute_of_hour,
                        CAST(EXTRACT(MINUTE FROM
                            to_timestamp(a.window_id * {_WINDOW_SECS})) AS INTEGER)
                    ) AS minute_of_hour,
                    COALESCE(w.day_of_week,
                        CAST(EXTRACT(DOW FROM
                            to_timestamp(a.window_id * {_WINDOW_SECS})) AS INTEGER)
                    ) AS day_of_week,
                    COALESCE(w.is_weekend,
                        EXTRACT(DOW FROM
                            to_timestamp(a.window_id * {_WINDOW_SECS})) IN (0, 6)
                    ) AS is_weekend,
                    COALESCE(w.day_of_month,
                        CAST(EXTRACT(DAY FROM
                            to_timestamp(a.window_id * {_WINDOW_SECS})) AS INTEGER)
                    ) AS day_of_month,
                    COALESCE(w.window_position_in_hour, CAST(
                        (EXTRACT(HOUR FROM to_timestamp(a.window_id * {_WINDOW_SECS})) * 720 +
                         EXTRACT(MINUTE FROM to_timestamp(a.window_id * {_WINDOW_SECS})) * 12 +
                         EXTRACT(SECOND FROM to_timestamp(a.window_id * {_WINDOW_SECS}))
                            / {_WINDOW_SECS})
                    AS INTEGER)) AS window_position_in_hour
                FROM all_ids a
                LEFT JOIN '{summary_path}' w ON a.window_id = w.window_id
                ORDER BY a.window_id
            ) TO '{tmp_path}' (FORMAT PARQUET, CODEC 'ZSTD')
        """)

        tmp_path.replace(summary_path)
        empty_added = total_span - existing
        logger.info("Filled %d empty windows (total span %d)", empty_added, total_span)
        return {"empty_windows_added": empty_added}
