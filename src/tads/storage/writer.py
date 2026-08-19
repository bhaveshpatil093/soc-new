import json
import uuid
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tads.constants import DatasetType
from tads.schema.raw import CANONICAL_RAW_SCHEMA, coerce_hit_to_canonical


class ParquetStorage:
    """Handles raw Parquet writing partitioned by date."""

    def __init__(self, dataset: DatasetType, base_dir: Path | str | None = None) -> None:
        assert dataset in ("july", "august"), "Invalid dataset namespace"
        self.dataset = dataset

        if base_dir is None:
            # Default to project_root/data/{dataset}/raw
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.base_dir = project_root / "data" / dataset / "raw"
            self.artifacts_dir = project_root / "artifacts" / dataset
        else:
            self.base_dir = Path(base_dir) / "data" / dataset / "raw"
            self.artifacts_dir = Path(base_dir) / "artifacts" / dataset

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir = self.artifacts_dir / "quarantine"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self._seen_events: OrderedDict[str, None] = OrderedDict()
        self._max_cache = 100000

    def _get_partition_dir(self, partition: str) -> Path:
        """Returns the directory for a partition, creating it if necessary."""
        p_dir = self.base_dir / partition
        assert f"/{self.dataset}/" in str(p_dir.absolute()), "Fatal: Attempted to access foreign dataset path!"
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
        quarantine_file = self.quarantine_dir / f"{run_id}_rejected.jsonl"

        quarantine_buffer = []

        for hit in batch:
            _id = str(hit.get("_id", ""))
            try:
                coerced = coerce_hit_to_canonical(hit)

                # Check duplicates using LRU
                cache_key = f"{_id}_{coerced['raw_timestamp']}"
                if cache_key in self._seen_events:
                    dropped["DUPLICATE_TIMESTAMP"] = dropped.get("DUPLICATE_TIMESTAMP", 0) + 1
                    # Don't quarantine duplicates, just count them.
                    # Reader will perform final exact deduplication.

                self._seen_events[cache_key] = None
                if len(self._seen_events) > self._max_cache:
                    self._seen_events.popitem(last=False)

                coerced_records.append(coerced)
            except ValueError as e:
                msg = str(e)
                if "MISSING_ID" in msg:
                    reason = "MISSING_ID"
                elif "MISSING_TIMESTAMP" in msg:
                    reason = "MISSING_TIMESTAMP"
                elif "INVALID_TIMESTAMP_FORMAT" in msg:
                    reason = "INVALID_TIMESTAMP"
                elif "FUTURE_TIMESTAMP" in msg:
                    reason = "FUTURE_TIMESTAMP"
                elif "OUT_OF_RANGE_TIMESTAMP" in msg:
                    reason = "OUT_OF_RANGE_TIMESTAMP"
                else:
                    reason = "SCHEMA_ERROR"

                dropped[reason] = dropped.get(reason, 0) + 1

                # Add to quarantine
                quarantine_buffer.append({
                    "reason": reason,
                    "error_msg": msg,
                    "raw_hit": hit
                })

        if quarantine_buffer:
            with open(quarantine_file, "a", encoding="utf-8") as f:
                for q_evt in quarantine_buffer:
                    f.write(json.dumps(q_evt, default=str) + "\n")

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
