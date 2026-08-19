import uuid
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


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
    ) -> Path:
        """
        Writes a batch of events to a distinct Parquet file.
        Using a stable batch_id ensures that if a batch is retried (at-least-once),
        we overwrite the previous attempt's file for this run, reducing duplicates at the source.
        If duplicates still persist across run_ids, they can be deduplicated at read time.
        """
        if not batch:
            raise ValueError("Batch is empty")

        p_dir = self._get_partition_dir(partition)

        if not batch_id:
            batch_id = str(uuid.uuid4())

        file_path = p_dir / f"{run_id}_batch_{batch_id}.parquet"

        # We need to flatten or handle nested dictionaries in the batch if necessary,
        # but pyarrow handles structs natively if schemas are consistent.
        # For simplicity, we just convert dicts to a PyArrow Table.
        # If schemas are jagged (highly likely in raw logs), pyarrow might fail to infer a rigid schema.
        # However, since this is a robust ingestion engine, we should just let pyarrow infer it
        # or convert it properly.
        table = pa.Table.from_pylist(batch)

        # ZSTD compression is fast and provides excellent compression ratio
        pq.write_table(table, file_path, compression="ZSTD")

        return file_path
