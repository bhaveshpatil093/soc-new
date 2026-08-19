import json
import os
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

class ExtractionCheckpoint(BaseModel):
    """Represents the state of an extraction process."""
    source: str = Field(..., description="The target index or data stream (source of extraction)")
    time_range: dict[str, str] = Field(..., description="Dictionary containing 'start' and 'end' ISO8601 bounds")
    search_after: list[Any] | None = Field(default=None, description="The sort values to resume from")
    partition: str = Field(..., description="Partition string, e.g. '2024-07'")
    event_count: int = Field(default=0, description="Total documents successfully processed so far")
    timestamp: str = Field(..., description="ISO8601 timestamp of when the checkpoint was last updated")
    software_version: str = Field(..., description="Version of the extraction software")


class CheckpointManager:
    """Manages atomic reads and writes of extraction checkpoints to disk."""

    def __init__(self, checkpoint_dir: Path | str | None = None) -> None:
        if checkpoint_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.checkpoint_dir = base_dir / "artifacts" / "checkpoints"
        else:
            self.checkpoint_dir = Path(checkpoint_dir)

        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, run_id: str) -> Path:
        return self.checkpoint_dir / f"{run_id}.json"

    def load(self, run_id: str) -> ExtractionCheckpoint | None:
        """Loads a checkpoint from disk if it exists."""
        path = self._get_path(run_id)
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return ExtractionCheckpoint(**data)
        except Exception as e:
            logger.error("Failed to load checkpoint", run_id=run_id, error=str(e))
            return None

    def save(self, run_id: str, checkpoint: ExtractionCheckpoint) -> None:
        """Atomically saves the checkpoint to disk."""
        path = self._get_path(run_id)
        tmp_path = path.with_suffix(".json.tmp")

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint.model_dump(), f, indent=2)

            # Atomic rename (POSIX ensures this is atomic, Windows may raise if file exists in older Python,
            # but Python 3.3+ os.replace is atomic on both platforms where possible)
            os.replace(tmp_path, path)
            logger.debug("Checkpoint saved", run_id=run_id, docs=checkpoint.event_count)
        except Exception as e:
            logger.error("Failed to save checkpoint", run_id=run_id, error=str(e))
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def clear(self, run_id: str) -> None:
        """Removes a checkpoint upon successful completion."""
        path = self._get_path(run_id)
        if path.exists():
            path.unlink()
            logger.info("Checkpoint cleared", run_id=run_id)
