import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from tads.constants import DatasetType
from tads.schema.raw import CANONICAL_RAW_SCHEMA


def compute_schema_hash() -> str:
    """Computes a SHA256 hash of the canonical PyArrow schema."""
    schema_str = CANONICAL_RAW_SCHEMA.to_string()
    return hashlib.sha256(schema_str.encode("utf-8")).hexdigest()


def compute_config_hash(config: dict[str, Any]) -> str:
    """Computes a SHA256 hash of a deterministic dictionary of configuration parameters."""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode("utf-8")).hexdigest()


def compute_file_checksum(filepath: Path) -> str:
    """Computes SHA256 checksum of a file in chunks."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read in 4K blocks
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class ExtractionManifest(BaseModel):
    run_id: str = Field(..., description="Unique identifier for the extraction run")
    source: str = Field(..., description="Target index or pattern")
    requested_start: str = Field(..., description="Requested start time")
    requested_end: str = Field(..., description="Requested end time")
    actual_min_timestamp: str | None = Field(default=None, description="Actual earliest timestamp seen")
    actual_max_timestamp: str | None = Field(default=None, description="Actual latest timestamp seen")
    event_count: int = Field(default=0, description="Total number of events extracted")
    partition_count: int = Field(default=0, description="Total number of partitions written")
    schema_version: int = Field(..., description="Version of the canonical schema used")
    schema_hash: str = Field(..., description="Hash of the exact canonical Arrow schema used")
    software_version: str = Field(..., description="Version of TADS used")
    configuration_hash: str = Field(..., description="Hash of the active settings during run")
    checksums: dict[str, str] = Field(default_factory=dict, description="Mapping of relative file path to SHA-256 checksum")
    status: Literal["IN_PROGRESS", "COMPLETED", "FAILED"] = Field(default="IN_PROGRESS")
    duration_seconds: float = Field(default=0.0, description="Total seconds taken to extract")
    dropped_events: dict[str, int] = Field(default_factory=dict, description="Counts of events dropped by reason")


class ManifestBuilder:
    """Handles lifecycle and generation of extraction manifests."""

    def __init__(self, dataset: DatasetType, base_dir: Path | str | None = None) -> None:
        assert dataset in ("july", "august"), "Invalid dataset namespace"
        self.dataset = dataset

        if base_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.manifest_dir = project_root / "artifacts" / dataset / "manifests"
            self.data_dir = project_root / "data" / dataset / "raw"
        else:
            self.manifest_dir = Path(base_dir) / "artifacts" / dataset / "manifests"
            self.data_dir = Path(base_dir) / "data" / dataset / "raw"

        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, run_id: str) -> Path:
        path = self.manifest_dir / f"{run_id}.json"
        assert f"/{self.dataset}/" in str(path.absolute()), "Fatal: Attempted to access foreign dataset path!"
        return path

    def initialize_run(
        self,
        run_id: str,
        source: str,
        start_time: str,
        end_time: str,
        batch_size: int,
        schema_version: int,
        software_version: str = "0.1.0"
    ) -> None:
        """Creates and saves the initial IN_PROGRESS manifest."""
        path = self._get_path(run_id)
        if path.exists():
            raise FileExistsError(f"Manifest for run {run_id} already exists. Manifests are immutable.")

        config = {
            "source": source,
            "start_time": start_time,
            "end_time": end_time,
            "batch_size": batch_size
        }

        manifest = ExtractionManifest(
            run_id=run_id,
            source=source,
            requested_start=start_time,
            requested_end=end_time,
            event_count=0,
            partition_count=0,
            schema_version=schema_version,
            schema_hash=compute_schema_hash(),
            software_version=software_version,
            configuration_hash=compute_config_hash(config),
            checksums={},
            status="IN_PROGRESS"
        )
        self._save(manifest)

    def _save(self, manifest: ExtractionManifest) -> None:
        """Atomically saves the manifest."""
        path = self._get_path(manifest.run_id)
        tmp_path = path.with_suffix(".json.tmp")

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)

        import os
        os.replace(tmp_path, path)

    def load(self, run_id: str) -> ExtractionManifest:
        """Loads a manifest from disk."""
        path = self._get_path(run_id)
        if not path.exists():
            raise FileNotFoundError(f"No manifest found for {run_id}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return ExtractionManifest(**data)

    def mark_completed(
        self,
        run_id: str,
        files_written: list[Path],
        actual_min_timestamp: str | None,
        actual_max_timestamp: str | None,
        event_count: int,
        partitions: set[str],
        duration_seconds: float,
        dropped_events: dict[str, int]
    ) -> None:
        """
        Transitions the manifest to COMPLETED, generating file checksums.
        Once completed, the manifest becomes strictly immutable.
        """
        manifest = self.load(run_id)
        if manifest.status == "COMPLETED":
            raise RuntimeError(f"Manifest {run_id} is already completed and is immutable.")

        checksums = {}
        for file_path in files_written:
            # Store relative path from the data_dir for portability
            try:
                rel_path = str(file_path.relative_to(self.data_dir))
            except ValueError:
                # Fallback to absolute if it's somehow not in data_dir
                rel_path = str(file_path)
            checksums[rel_path] = compute_file_checksum(file_path)

        manifest.actual_min_timestamp = actual_min_timestamp
        manifest.actual_max_timestamp = actual_max_timestamp
        manifest.event_count = event_count
        manifest.partition_count = len(partitions)
        manifest.checksums = checksums
        manifest.status = "COMPLETED"
        manifest.duration_seconds = duration_seconds
        manifest.dropped_events = dropped_events

        self._save(manifest)

    def mark_failed(self, run_id: str, event_count: int) -> None:
        """Transitions the manifest to FAILED."""
        manifest = self.load(run_id)
        if manifest.status == "COMPLETED":
            raise RuntimeError(f"Manifest {run_id} is already completed and is immutable.")

        manifest.status = "FAILED"
        manifest.event_count = event_count
        self._save(manifest)
