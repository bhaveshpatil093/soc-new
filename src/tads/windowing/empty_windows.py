"""
Empty window materialization.

When MATERIALIZE_EMPTY_WINDOWS is True (the default), this module fills in
explicit zero-count rows for every 5-second window in [min_window_id,
max_window_id] that has no events.  This guarantees the window summary
forms a contiguous, regularly-spaced time series — critical for any
sequence model that relies on fixed 5-second ticks.

Design rationale
----------------
Silence is signal.  A SOC environment that normally produces 50 events per
window and suddenly produces 0 is potentially anomalous.  If empty windows
are simply absent, a sequence model will see window N followed by window
N+K (where K > 1), destroying temporal continuity and making consecutive
silence invisible.

By materializing empty windows as explicit rows (event_count=0, all
features null/zero), the downstream model always sees a regular grid and
can detect "N consecutive silent windows" as a first-class pattern.

The policy is governed by a SINGLE constant:
    tads.constants.MATERIALIZE_EMPTY_WINDOWS

No other module should independently decide whether to include or exclude
empty windows.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from tads.constants import MATERIALIZE_EMPTY_WINDOWS, WINDOW_SIZE_MS

logger = logging.getLogger(__name__)

# Seconds-per-window, derived from the canonical constant
_WINDOW_SECS = WINDOW_SIZE_MS // 1000


def materialize_empty_windows(
    window_summary_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, int]:
    """Fill gaps in a window summary with explicit zero-count rows.

    Parameters
    ----------
    window_summary_path:
        Path to the existing ``window_summary.parquet`` produced by
        :class:`~tads.windowing.indexer.WindowIndexer`.
    output_path:
        Where to write the dense (gap-filled) summary.  If *None*, the
        input file is overwritten in-place (atomic via temp + rename).

    Returns
    -------
    dict with keys ``total_windows``, ``non_empty_windows``,
    ``empty_windows_added``.
    """
    if not MATERIALIZE_EMPTY_WINDOWS:
        logger.info("MATERIALIZE_EMPTY_WINDOWS is False — skipping.")
        return {"total_windows": 0, "non_empty_windows": 0, "empty_windows_added": 0}

    src = Path(window_summary_path)
    dst = Path(output_path) if output_path else src
    tmp = dst.with_suffix(".tmp.parquet")

    conn = duckdb.connect(database=":memory:")
    conn.execute("SET TimeZone='UTC'")

    try:
        # Load existing summary
        conn.execute(f"""
            CREATE TABLE ws AS
            SELECT * FROM '{src}'
        """)

        stats = conn.execute("""
            SELECT MIN(window_id) AS lo, MAX(window_id) AS hi, COUNT(*) AS n
            FROM ws
        """).fetchone()

        if stats is None or stats[0] is None:
            return {"total_windows": 0, "non_empty_windows": 0, "empty_windows_added": 0}

        lo, hi, existing_count = int(stats[0]), int(stats[1]), int(stats[2])
        total_span = hi - lo + 1

        # Generate a contiguous series of all window_ids in [lo, hi]
        conn.execute(f"""
            CREATE TABLE all_ids AS
            SELECT
                CAST(lo + i AS BIGINT) AS window_id
            FROM generate_series(0, {total_span - 1}) AS t(i),
                 (SELECT {lo} AS lo)
        """)

        # Left join to produce the dense summary
        conn.execute(f"""
            COPY (
                SELECT
                    a.window_id,
                    to_timestamp(a.window_id * {_WINDOW_SECS})  AS window_start,
                    to_timestamp(a.window_id * {_WINDOW_SECS} + {_WINDOW_SECS}) AS window_end,
                    COALESCE(ws.event_count, 0) AS event_count
                FROM all_ids a
                LEFT JOIN ws ON a.window_id = ws.window_id
                ORDER BY a.window_id
            ) TO '{tmp}' (FORMAT PARQUET, CODEC 'ZSTD')
        """)

        # Atomic rename
        tmp.replace(dst)

        empty_added = total_span - existing_count
        logger.info(
            "Materialized %d empty windows (total %d, non-empty %d)",
            empty_added, total_span, existing_count,
        )
        return {
            "total_windows": total_span,
            "non_empty_windows": existing_count,
            "empty_windows_added": empty_added,
        }
    finally:
        conn.close()
