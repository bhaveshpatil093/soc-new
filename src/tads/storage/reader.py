from pathlib import Path

import polars as pl

from tads.constants import DatasetType


class ParquetReader:
    """Handles reading and validating Canonical Parquet data into Polars LazyFrames."""

    def __init__(self, dataset: DatasetType, base_dir: Path | str | None = None) -> None:
        assert dataset in ("july", "august"), "Invalid dataset namespace"
        self.dataset = dataset

        if base_dir is None:
            # Default to project_root/data/{dataset}/raw
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.base_dir = project_root / "data" / dataset / "raw"
        else:
            self.base_dir = Path(base_dir) / "data" / dataset / "raw"

        if not self.base_dir.exists():
            raise FileNotFoundError(f"Base data directory not found: {self.base_dir}")

    def load_and_deduplicate(self, partition: str, unique_id_field: str = "_id") -> pl.LazyFrame:
        """
        Loads all Parquet files in a partition into a lazy frame,
        and explicitly deduplicates them across exactly-once boundaries.
        Only processes partitions that have been finalized (i.e. possess a manifest marker).

        Args:
            partition: The directory partition (e.g., '2024-07')
            unique_id_field: The column uniquely identifying events (defaults to '_id')

        Returns:
            A deduplicated Polars LazyFrame ready for downstream windowing.
        """
        partition_dir = self.base_dir / partition
        if not partition_dir.exists():
            raise FileNotFoundError(f"Partition directory not found: {partition_dir}")

        # Check if the partition is finalized by checking for ANY manifest.
        # In a real system, you might check if all expected run_ids have manifests.
        manifests = list(partition_dir.glob("manifest_*.json"))
        if not manifests:
            raise RuntimeError(f"Partition {partition} is not finalized (missing manifest).")

        # Read all parquet files in the partition directory
        files_pattern = str(partition_dir / "*.parquet")

        # Use lazy scanning to avoid blowing up memory on huge datasets
        lf = pl.scan_parquet(files_pattern)

        # Explicit deduplication across checkpoint boundaries
        lf_dedup = lf.unique(subset=[unique_id_field], maintain_order=False)

        return lf_dedup
