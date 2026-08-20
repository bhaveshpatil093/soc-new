"""
Robust Feature Statistics Baseline.

Calculates comprehensive exact statistics for telemetry features, explicitly
separating heavy-tailed features (using median/MAD/IQR) from well-behaved
features (using mean/std) for downstream calibration.
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import pyarrow as pa

from tads.baselines.base import BaseBaseline

if TYPE_CHECKING:
    from collections.abc import Sequence


class RobustFeatureStatisticsBaseline(BaseBaseline):  # type: ignore[misc]
    """
    Computes exact statistics over July data using DuckDB.

    Generates: mean, std, median, MAD, IQR, p25, p75, p90, p95, p99, p99_9
    Exports results to a Parquet file for inference.
    """

    def __init__(
        self,
        features: Sequence[str],
        standard_features: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.features = set(features)
        self.standard_features = set(standard_features or [])

        self._temp_db_path = tempfile.mktemp(suffix=".db")
        self._con = duckdb.connect(self._temp_db_path)
        self._con.execute("CREATE TABLE staging_features (feature_name VARCHAR, value DOUBLE)")

    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        if not isinstance(data, pa.Table):
            if not data:
                return
            data = pa.Table.from_pylist(data)

        # Unpivot the columns we care about into long format: (feature_name, value)
        # Using DuckDB's UNPIVOT

        # Check which features exist in this batch
        available = [f for f in self.features if f in data.column_names]
        if not available:
            return

        cols = ", ".join(available)

        query = f"""
            INSERT INTO staging_features
            SELECT feature_name, value
            FROM data
            UNPIVOT (
                value FOR feature_name IN ({cols})
            )
            WHERE value IS NOT NULL
        """
        self._con.execute(query)

    def save(self, version_dir: Path, name: str) -> None:
        """
        Compute robust statistics for all features and export to Parquet.
        """
        parquet_path = version_dir / f"{name}.parquet"

        # First, compute basic exact quantiles and moments
        # For MAD, we need the median first. We'll compute median in a CTE.
        query = """
        CREATE TABLE final_stats AS
        WITH base_stats AS (
            SELECT
                feature_name,
                AVG(value) as mean,
                STDDEV(value) as std,
                quantile_cont(value, 0.5) as median,
                quantile_cont(value, 0.25) as p25,
                quantile_cont(value, 0.75) as p75,
                quantile_cont(value, 0.90) as p90,
                quantile_cont(value, 0.95) as p95,
                quantile_cont(value, 0.99) as p99,
                quantile_cont(value, 0.999) as p99_9
            FROM staging_features
            GROUP BY feature_name
        ),
        mad_stats AS (
            SELECT
                f.feature_name,
                quantile_cont(ABS(f.value - b.median), 0.5) as mad
            FROM staging_features f
            JOIN base_stats b ON f.feature_name = b.feature_name
            GROUP BY f.feature_name
        )
        SELECT
            b.feature_name,
            b.mean,
            COALESCE(b.std, 0.0) as std,
            b.median,
            m.mad,
            (b.p75 - b.p25) as iqr,
            b.p25,
            b.p75,
            b.p90,
            b.p95,
            b.p99,
            b.p99_9
        FROM base_stats b
        JOIN mad_stats m ON b.feature_name = m.feature_name
        """

        self._con.execute(query)

        # Now add calibration_method column
        # Default is 'robust', except for features strictly declared as 'standard'

        # We can update this in DuckDB by adding a column
        self._con.execute("ALTER TABLE final_stats ADD COLUMN calibration_method VARCHAR")

        # Convert standard_features to a format for SQL IN clause
        if self.standard_features:
            std_list = ", ".join([f"'{f}'" for f in self.standard_features])
            self._con.execute(f"UPDATE final_stats SET calibration_method = 'standard' WHERE feature_name IN ({std_list})")

        self._con.execute("UPDATE final_stats SET calibration_method = 'robust' WHERE calibration_method IS NULL")

        # Export to Parquet
        self._con.execute(f"COPY final_stats TO '{parquet_path}' (FORMAT PARQUET)")

        self._con.close()
        with contextlib.suppress(OSError):
            Path(self._temp_db_path).unlink(missing_ok=True)

    def load(self, version_dir: Path, name: str) -> None:
        """Load stats from Parquet for inference lookups."""
        parquet_path = version_dir / f"{name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"Missing parquet file for feature statistics baseline: {parquet_path}")

        self._con = duckdb.connect(":memory:")
        self._con.execute(f"CREATE TABLE final_stats AS SELECT * FROM read_parquet('{parquet_path}')")

        # Cache stats in memory for O(1) lookups during inference since there are only
        # a few hundred features at most.
        self._stats_cache: dict[str, dict[str, Any]] = {}

        # We use arrow or fetchall since pandas is not installed
        res = self._con.execute("SELECT * FROM final_stats").fetchall()
        columns = [desc[0] for desc in self._con.description]

        for row in res:
            row_dict = dict(zip(columns, row, strict=False))
            self._stats_cache[row_dict["feature_name"]] = row_dict

    def get_statistics(self, feature_name: str) -> dict[str, Any] | None:
        """Retrieve the precomputed statistics for a feature."""
        return getattr(self, "_stats_cache", {}).get(feature_name)

    def __del__(self) -> None:
        try:
            if hasattr(self, "_con"):
                self._con.close()
        except Exception:
            pass
