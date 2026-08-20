"""
Human validation mechanism for appending labels to candidates/episodes.

Strictly append-only layer. Does not mutate original inference artifacts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AnnotationLabel(str, Enum):
    """Permitted human validation labels."""

    BENIGN = "BENIGN"
    EXPECTED_CHANGE = "EXPECTED_CHANGE"
    SUSPICIOUS = "SUSPICIOUS"
    SECURITY_RELEVANT = "SECURITY_RELEVANT"
    UNKNOWN = "UNKNOWN"


@dataclass
class Annotation:
    """A single human validation event."""

    target_id: str
    target_type: str
    label: AnnotationLabel
    analyst: str
    timestamp: str
    notes: str | None = None


class AnnotationStore:
    """Append-only annotation datastore."""

    def __init__(self, storage_path: str = "data/annotations.jsonl") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history in memory for querying
        self._history: list[Annotation] = []
        if self.storage_path.exists():
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    # Convert raw string back to enum
                    data["label"] = AnnotationLabel(data["label"])
                    self._history.append(Annotation(**data))

    def append(self, target_id: str, target_type: str, label: AnnotationLabel, analyst: str, notes: str | None = None) -> None:
        """Append a new annotation to the log."""
        ann = Annotation(
            target_id=target_id,
            target_type=target_type,
            label=label,
            analyst=analyst,
            timestamp=datetime.now(UTC).isoformat(),
            notes=notes,
        )

        # Append-only write to disk
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(ann)) + "\n")

        self._history.append(ann)
        logger.info(f"Appended {label.value} annotation to {target_id} by {analyst}")

    def get_history(self, target_id: str) -> list[Annotation]:
        """Retrieve the complete chronological annotation history for a target."""
        return [ann for ann in self._history if ann.target_id == target_id]
