"""
Baseline Manager and Storage orchestration for the persistent July baseline system.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tads.baselines.base import BaseBaseline, ImmutableBaselineError

if TYPE_CHECKING:
    import pyarrow as pa

BASELINE_DIR = Path(".data/baselines")


class BaselineManager:
    """
    Orchestrates training, saving, and loading a versioned, immutable suite of baseline components.
    """

    def __init__(self, components: dict[str, BaseBaseline]) -> None:
        self.components = components
        self.version_id: str | None = None
        self.is_frozen = False

    def fit(self, data: pa.Table | list[dict[str, Any]], timestamp_col: str = "window_start") -> None:
        """
        Train all registered baseline components on the provided data.

        Raises ImmutableBaselineError if the manager is already frozen.
        Raises TemporalLeakageError if the data exceeds the July boundary.
        """
        if self.is_frozen:
            raise ImmutableBaselineError("BaselineManager is frozen. Create a new instance to train a new version.")
        for comp in self.components.values():
            comp.fit(data, timestamp_col=timestamp_col)

    def save(self, version_id: str | None = None) -> str:
        """
        Save all components to disk, freeze them, and return the version_id.
        """
        if self.is_frozen:
            raise ImmutableBaselineError("Cannot save an already frozen baseline over again.")

        if version_id is None:
            version_id = f"v_{uuid.uuid4().hex[:8]}"

        version_dir = BASELINE_DIR / version_id
        if version_dir.exists() and (version_dir / ".frozen").exists():
            raise ImmutableBaselineError(f"Version {version_id} is already frozen and cannot be overwritten.")

        version_dir.mkdir(parents=True, exist_ok=True)

        # Serialize each component
        for name, comp in self.components.items():
            state_dict = comp.to_dict()
            state_file = version_dir / f"{name}.json"
            state_file.write_text(json.dumps(state_dict, indent=2))

        # Freeze by touching the sentinel file
        (version_dir / ".frozen").touch()

        # Update runtime state to frozen
        self.version_id = version_id
        self.is_frozen = True
        for comp in self.components.values():
            comp.is_frozen = True

        return version_id

    @classmethod
    def load(cls, version_id: str, components: dict[str, BaseBaseline]) -> BaselineManager:
        """
        Load a specific frozen baseline version from disk.
        """
        version_dir = BASELINE_DIR / version_id
        if not version_dir.exists():
            raise ValueError(f"Baseline version '{version_id}' not found at {version_dir}.")
        if not (version_dir / ".frozen").exists():
            raise ImmutableBaselineError(f"Baseline version '{version_id}' is not frozen (training may have been incomplete).")

        manager = cls(components)
        for name, comp in manager.components.items():
            state_file = version_dir / f"{name}.json"
            if state_file.exists():
                raw_state = json.loads(state_file.read_text())
                comp.from_dict(raw_state)
            # Ensure loaded components are also frozen
            comp.is_frozen = True

        manager.version_id = version_id
        manager.is_frozen = True
        return manager
