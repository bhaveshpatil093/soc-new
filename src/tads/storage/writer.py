import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tads.schema.raw import CANONICAL_RAW_SCHEMA, coerce_hit_to_canonical


class ParquetStorage:
    """Handles partitioned writing of event batches to local Parquet files."""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.base_dir = project_root / "data" / "raw"
        else:
            self.base_dir = Path(base_dir)

    def _get_partition_dir(self, partition: str) -> Path:
        p_dir = self.base_dir / partition
        p_dir.mkdir(parents=True, exist_ok=True)
        return p_dir

    def write_batch(
        self,
        batch: list[dict[str, Any]],
        partition: str,
        run_id: str,
        batch_id: str | None = None
    ) -> tuple[Path | None, dict[str, int]]:
        """
        Writes a batch of events to a distinct Parquet file.
        Enforces canonical schema strictly. Drops events that violate the schema,
        returning a tuple of the written file path (if any records survived) and
        a dictionary mapping reason codes to the count of dropped events.
        """
        if not batch:
            return None, {}

        p_dir = self._get_partition_dir(partition)

        if not batch_id:
            batch_id = str(uuid.uuid4())

        file_path = p_dir / f"{run_id}_batch_{batch_id}.parquet"

        coerced_records = []
        dropped: dict[str, int] = {}

        for hit in batch:
            try:
                coerced = coerce_hit_to_canonical(hit)
                coerced_records.append(coerced)
            except ValueError as e:
                msg = str(e).lower()
                if "missing required field '_id'" in msg:
                    reason = "MISSING_ID"
                elif "missing required field '@timestamp'" in msg:
                    reason = "MISSING_TIMESTAMP"
                elif "invalid '@timestamp'" in msg:
                    reason = "INVALID_TIMESTAMP"
                else:
                    reason = "SCHEMA_ERROR"

                dropped[reason] = dropped.get(reason, 0) + 1

        if not coerced_records:
            return None, dropped

        # Enforce canonical PyArrow schema
        # If any types are fundamentally incompatible and cannot be cast, this will raise.
        table = pa.Table.from_pylist(coerced_records, schema=CANONICAL_RAW_SCHEMA)

        # We write a single row group per batch file.
        # It is highly recommended that the ingestion batch size is set to ~100,000
        # so that each row group is approximately 100k rows. This optimally balances
        # memory usage (~50MB peak) with vectorization read efficiency in DuckDB.
        pq.write_table(table, file_path, compression="ZSTD")

        return file_path, dropped

    def finalize_partition(self, partition: str, run_id: str, total_docs: int) -> Path:
        """
        Writes a manifest.json marker indicating the partition (or at least this run's
        contribution to the partition) completed successfully.
        Downstream readers should only consider partitions/files that are finalized.
        """
        p_dir = self._get_partition_dir(partition)
        manifest_path = p_dir / f"manifest_{run_id}.json"

        manifest = {
            "partition": partition,
            "run_id": run_id,
            "total_documents": total_docs,
            "schema_version": "1.0",
            "finalized_at": datetime.now(UTC).isoformat()
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest_path
