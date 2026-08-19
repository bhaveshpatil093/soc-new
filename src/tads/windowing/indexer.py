import logging
from pathlib import Path

import duckdb

from tads.constants import WINDOW_SIZE_MS

logger = logging.getLogger(__name__)

class WindowIndexer:
    """
    Scans a Parquet dataset and generates semantic window index artifacts.
    Output consists of an event index (_id -> window_id) and a window summary
    (window_id -> start, end, event_count).
    """

    def __init__(self, dataset: str, base_dir: Path | str | None = None) -> None:
        assert dataset in ("july", "august"), "Invalid dataset namespace"
        self.dataset = dataset

        if base_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.base_dir = project_root
        else:
            self.base_dir = Path(base_dir)

        self.data_dir = self.base_dir / "data" / dataset / "raw"
        self.index_dir = self.base_dir / "data" / dataset / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def generate_index(self) -> dict[str, str]:
        """
        Executes out-of-core queries to generate indexing parquets.
        Returns the absolute paths to the generated artifacts.
        """
        pattern = str(self.data_dir / "*" / "compacted.parquet")

        import glob
        if not glob.glob(pattern):
            logger.warning(f"No compacted parquet files found for {self.dataset} at {pattern}")
            return {}

        conn = duckdb.connect(database=':memory:')
        conn.execute("SET TimeZone='UTC'")

        event_index_path = self.index_dir / "event_index.parquet"
        window_summary_path = self.index_dir / "window_summary.parquet"

        try:
            # Drop existing just in case
            if event_index_path.exists():
                event_index_path.unlink()
            if window_summary_path.exists():
                window_summary_path.unlink()

            # The exact mathematical assignment of a window_id from epoch ms
            # Duckdb epoch() returns seconds as float.
            # We want milliseconds, so epoch(timestamp) * 1000
            # Floor div by WINDOW_SIZE_MS (default 5000)

            # 1. Generate the granular Event Index
            event_index_query = f"""
                COPY (
                    SELECT
                        _id,
                        CAST(FLOOR((epoch("@timestamp") * 1000) / {WINDOW_SIZE_MS}) AS BIGINT) as window_id
                    FROM '{pattern}'
                ) TO '{event_index_path}' (FORMAT PARQUET, CODEC 'ZSTD');
            """
            conn.execute(event_index_query)

            # 2. Generate the Window Summary
            # We calculate window_start dynamically from the integer window_id
            # window_start = to_timestamp(window_id * 5)
            # window_end = to_timestamp((window_id * 5) + 5)
            summary_query = f"""
                COPY (
                    SELECT
                        window_id,
                        to_timestamp(window_id * ({WINDOW_SIZE_MS} / 1000)) as window_start,
                        to_timestamp((window_id * ({WINDOW_SIZE_MS} / 1000)) + ({WINDOW_SIZE_MS} / 1000)) as window_end,
                        COUNT(*) as event_count
                    FROM '{event_index_path}'
                    GROUP BY window_id
                    ORDER BY window_id
                ) TO '{window_summary_path}' (FORMAT PARQUET, CODEC 'ZSTD');
            """
            conn.execute(summary_query)

            return {
                "event_index": str(event_index_path),
                "window_summary": str(window_summary_path)
            }

        finally:
            conn.close()
