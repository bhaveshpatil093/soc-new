"""
Frequency Baseline Components.

Provides exact frequency counting (e.g. unique values and their frequencies) for
various entity types and relationships, strictly bounding memory usage.
"""

from __future__ import annotations

import collections
import contextlib
import tempfile
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa

from tads.baselines.base import BaseBaseline


class InMemoryFrequencyBaseline(BaseBaseline):  # type: ignore[misc]
    """
    In-memory frequency tracker for low-to-medium cardinality relationships.
    Uses collections.Counter.
    Raises MemoryError if unique keys exceed max_keys threshold.
    """

    def __init__(self, fields: list[str], max_keys: int = 5_000_000, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fields = fields
        self.max_keys = max_keys
        self.state["frequencies"] = collections.Counter()

    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        freqs = self.state["frequencies"]

        if isinstance(data, pa.Table):
            # Convert only requested columns
            cols = [data.column(f).to_pylist() for f in self.fields if f in data.column_names]
            if len(cols) == len(self.fields):
                # zip them together
                for row_vals in zip(*cols, strict=False):
                    if all(v is not None for v in row_vals):
                        key = row_vals[0] if len(self.fields) == 1 else tuple(row_vals)
                        freqs[key] += 1
        else:
            for row in data:
                vals = [row.get(f) for f in self.fields]
                if all(v is not None for v in vals):
                    key = vals[0] if len(self.fields) == 1 else tuple(vals)
                    freqs[key] += 1

        if len(freqs) > self.max_keys:
            raise MemoryError(
                f"InMemoryFrequencyBaseline exceeded safety cap of {self.max_keys} keys. "
                "Promote this baseline to DuckDBFrequencyBaseline to prevent OOM kills."
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert counter to dict. Convert tuple keys to string/list for JSON."""
        # For simplicity in JSON, we convert tuple keys to a string representation
        # or we just store them as lists of key-value pairs.
        kv_pairs = []
        for k, v in self.state["frequencies"].items():
            if isinstance(k, tuple):
                kv_pairs.append([list(k), v])
            else:
                kv_pairs.append([k, v])
        return {"frequencies_kv": kv_pairs}

    def from_dict(self, data: dict[str, Any]) -> None:
        freqs: collections.Counter[Any] = collections.Counter()
        for k, v in data.get("frequencies_kv", []):
            if isinstance(k, list):
                freqs[tuple(k)] = v
            else:
                freqs[k] = v
        self.state["frequencies"] = freqs

    def get_frequency(self, *key_vals: str) -> int:
        """Query the frequency of a specific key."""
        key = key_vals[0] if len(self.fields) == 1 else tuple(key_vals)
        return self.state["frequencies"].get(key, 0)

    def get_total_count(self) -> int:
        """Get the total number of events recorded."""
        return sum(self.state["frequencies"].values())


class DuckDBFrequencyBaseline(BaseBaseline):  # type: ignore[misc]
    """
    Disk-backed exact frequency tracker for high/unbounded cardinality relationships.
    Uses DuckDB to aggregate counts on disk during fit(), exporting to a Parquet file
    on save(), and querying via DuckDB views on load().
    """

    def __init__(self, fields: list[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fields = fields
        # Temporary DB file used during training
        self._temp_db_path = tempfile.mktemp(suffix=".db")
        self._con = duckdb.connect(self._temp_db_path)
        self._setup_db()

    def _setup_db(self) -> None:
        # Create staging table
        cols_def = ", ".join([f"{f} VARCHAR" for f in self.fields])
        self._con.execute(f"CREATE TABLE IF NOT EXISTS staging_freq ({cols_def}, count BIGINT)")

    def _fit(self, data: pa.Table | list[dict[str, Any]]) -> None:
        if not isinstance(data, pa.Table):
            # Convert list of dicts to pa.Table for DuckDB
            if not data:
                return
            data = pa.Table.from_pylist(data)

        # Ensure required columns exist
        missing = [f for f in self.fields if f not in data.column_names]
        if missing:
            return  # Skip if fields are missing in this window

        # Select only the relevant columns
        cols = ", ".join(self.fields)

        # Insert into DuckDB directly from PyArrow table (referenced as 'data')
        query = f"""
            INSERT INTO staging_freq
            SELECT {cols}, COUNT(*)
            FROM data
            WHERE {' AND '.join(f"{f} IS NOT NULL" for f in self.fields)}
            GROUP BY {cols}
        """
        self._con.execute(query)

    def save(self, version_dir: Path, name: str) -> None:
        """Compact the staging table and export to Parquet."""
        parquet_path = version_dir / f"{name}.parquet"
        cols = ", ".join(self.fields)

        # Compact staging into a final table (summing the intermediate counts)
        self._con.execute(f"""
            CREATE TABLE final_freq AS
            SELECT {cols}, SUM(count) as c
            FROM staging_freq
            GROUP BY {cols}
        """)

        # Export
        self._con.execute(f"COPY final_freq TO '{parquet_path}' (FORMAT PARQUET)")

        # We can close the temp connection now
        self._con.close()
        with contextlib.suppress(OSError):
            Path(self._temp_db_path).unlink(missing_ok=True)

    def load(self, version_dir: Path, name: str) -> None:
        """Connect to in-memory DuckDB and map the Parquet file."""
        parquet_path = version_dir / f"{name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"Missing parquet file for DuckDB frequency baseline: {parquet_path}")

        self._con = duckdb.connect(":memory:")
        self._con.execute(f"CREATE VIEW final_freq AS SELECT * FROM read_parquet('{parquet_path}')")

        # Optional: create an index if we plan to do lots of point lookups?
        # Views cannot be indexed directly, but point lookup against parquet is reasonable.
        # If speed is critical, we could load it into a table and index it:
        # self._con.execute(f"CREATE TABLE final_freq AS SELECT * FROM read_parquet('{parquet_path}')")
        # self._con.execute(f"CREATE INDEX idx_final_freq ON final_freq({', '.join(self.fields)})")

    def get_frequency(self, *key_vals: str) -> int:
        """Query the frequency of a specific key."""
        if len(key_vals) != len(self.fields):
            raise ValueError(f"Expected {len(self.fields)} key values, got {len(key_vals)}")

        where_clause = " AND ".join(f"{f} = ?" for f in self.fields)
        res = self._con.execute(f"SELECT c FROM final_freq WHERE {where_clause}", list(key_vals)).fetchone()
        return res[0] if res else 0

    def get_total_count(self) -> int:
        """Get the total number of events recorded."""
        res = self._con.execute("SELECT SUM(c) FROM final_freq").fetchone()
        return res[0] if res and res[0] else 0

    def __del__(self) -> None:
        try:
            if hasattr(self, "_con"):
                self._con.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# Concrete Implementations
# ------------------------------------------------------------------

class UserFrequencyBaseline(InMemoryFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["user_name"], **kwargs)

class IpFrequencyBaseline(InMemoryFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["source_ip"], **kwargs)

class HostFrequencyBaseline(InMemoryFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["host_name"], **kwargs)

class ProcessFrequencyBaseline(InMemoryFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["process_name"], **kwargs)

class UserHostFrequencyBaseline(InMemoryFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["user_name", "host_name"], **kwargs)

class HostProcessFrequencyBaseline(InMemoryFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["host_name", "process_name"], **kwargs)

class UserIpFrequencyBaseline(DuckDBFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["user_name", "source_ip"], **kwargs)

class IpHostFrequencyBaseline(DuckDBFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["source_ip", "host_name"], **kwargs)

class ProcessCommandFrequencyBaseline(DuckDBFrequencyBaseline):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(fields=["process_name", "process_command_line"], **kwargs)

