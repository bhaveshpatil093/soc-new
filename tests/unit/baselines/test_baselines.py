"""
Tests for the persistent July baseline system.

Covers:
- Temporal leakage guard (Strict Train/Test Separation)
- Immutability and freeze states
- Versioning and persistence (save/load)
- Correctness of Baseline Categories
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pyarrow as pa
import pytest

from tads.baselines.base import ImmutableBaselineError
from tads.baselines.components import (
    FeatureStatisticsBaseline,
    GlobalDistributionBaseline,
    RelationshipFrequencyBaseline,
    TemporalStatisticsBaseline,
    UserDistributionBaseline,
)
from tads.baselines.manager import BaselineManager
from tads.models.base import TemporalLeakageError

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def clean_baseline_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirects the BASELINE_DIR to a temporary directory for tests."""
    monkeypatch.setattr("tads.baselines.manager.BASELINE_DIR", tmp_path)
    return tmp_path


# ------------------------------------------------------------------
# Temporal Leakage Guard Tests
# ------------------------------------------------------------------
class TestTemporalLeakageGuard:
    def test_august_data_raises_temporal_leakage_error_pyarrow(self) -> None:
        """
        Validation Gate: Demonstrate the July-only runtime guard actually fires
        by attempting to fit a baseline component with August-range data mixed in.
        """
        # Create data with one July timestamp and one August timestamp
        leakage_data = pa.table({
            "window_start": [
                datetime(2025, 7, 15, 12, 0, 0, tzinfo=UTC),
                datetime(2025, 8, 2, 10, 0, 0, tzinfo=UTC)  # AUGUST LEAKAGE
            ],
            "user_name": ["alice", "bob"]
        })

        baseline = UserDistributionBaseline()

        # The guard must fire and prevent the fit
        with pytest.raises(TemporalLeakageError, match="Temporal leakage detected"):
            baseline.fit(leakage_data)

    def test_august_data_raises_temporal_leakage_error_dicts(self) -> None:
        """Test leakage guard with list of dicts."""
        leakage_data = [
            {"window_start": datetime(2025, 7, 15, tzinfo=UTC)},
            {"window_start": datetime(2025, 8, 2, tzinfo=UTC)} # AUGUST LEAKAGE
        ]

        baseline = UserDistributionBaseline()

        with pytest.raises(TemporalLeakageError, match="Temporal leakage detected"):
            baseline.fit(leakage_data)

    def test_july_data_passes_guard(self) -> None:
        """Pure July data should proceed without error."""
        valid_data = pa.table({
            "window_start": [
                datetime(2025, 7, 1, tzinfo=UTC),
                datetime(2025, 7, 31, 23, 59, 59, tzinfo=UTC)
            ],
            "user_name": ["alice", "bob"]
        })

        baseline = UserDistributionBaseline()
        baseline.fit(valid_data)
        assert baseline.state["known_entities"] == {"alice", "bob"}


# ------------------------------------------------------------------
# Immutability and Versioning Tests
# ------------------------------------------------------------------
class TestImmutabilityAndVersioning:
    def test_baseline_manager_save_and_freeze(self, clean_baseline_dir: Path) -> None:
        """Saving a baseline creates versioned dir, serializes state, and freezes."""
        manager = BaselineManager({
            "users": UserDistributionBaseline(),
            "global": GlobalDistributionBaseline()
        })

        data = pa.table({
            "window_start": [datetime(2025, 7, 1, tzinfo=UTC)],
            "user_name": ["alice"],
            "event_category": ["network"]
        })

        manager.fit(data)
        assert not manager.is_frozen

        version_id = manager.save()

        # Verify persistence
        version_dir = clean_baseline_dir / version_id
        assert version_dir.exists()
        assert (version_dir / ".frozen").exists()
        assert (version_dir / "users.json").exists()
        assert (version_dir / "global.json").exists()

        # Verify memory state is frozen
        assert manager.is_frozen
        assert manager.components["users"].is_frozen

    def test_modifying_frozen_baseline_raises_error(self, clean_baseline_dir: Path) -> None:
        """Once frozen, calling fit() or save() raises an error."""
        manager = BaselineManager({"users": UserDistributionBaseline()})
        manager.save()

        data = pa.table({"window_start": [datetime(2025, 7, 1, tzinfo=UTC)], "user_name": ["alice"]})

        with pytest.raises(ImmutableBaselineError, match="BaselineManager is frozen"):
            manager.fit(data)

        with pytest.raises(ImmutableBaselineError, match="Cannot save an already frozen baseline"):
            manager.save()

        with pytest.raises(ImmutableBaselineError, match="Cannot fit a frozen baseline"):
            manager.components["users"].fit(data)

    def test_load_rehydrates_frozen_baseline(self, clean_baseline_dir: Path) -> None:
        """Loading a baseline reconstructs state and ensures it is frozen."""
        manager1 = BaselineManager({"users": UserDistributionBaseline()})
        data = pa.table({"window_start": [datetime(2025, 7, 1, tzinfo=UTC)], "user_name": ["alice"]})
        manager1.fit(data)
        version_id = manager1.save()

        # New instance, loading from disk
        manager2 = BaselineManager.load(version_id, {"users": UserDistributionBaseline()})

        assert manager2.version_id == version_id
        assert manager2.is_frozen
        assert manager2.components["users"].is_frozen
        assert manager2.components["users"].state["known_entities"] == {"alice"}

    def test_load_unfrozen_raises_error(self, clean_baseline_dir: Path) -> None:
        """If a baseline is missing the .frozen sentinel, it cannot be loaded."""
        version_id = "v_broken"
        version_dir = clean_baseline_dir / version_id
        version_dir.mkdir()
        (version_dir / "users.json").write_text('{}')
        # We intentionally do not create the .frozen file

        with pytest.raises(ImmutableBaselineError, match="not frozen"):
            BaselineManager.load(version_id, {"users": UserDistributionBaseline()})


# ------------------------------------------------------------------
# Component Correctness Tests
# ------------------------------------------------------------------
class TestBaselineComponents:
    def test_relationship_frequency_baseline(self) -> None:
        data = pa.table({
            "window_start": [datetime(2025, 7, 1, tzinfo=UTC)] * 3,
            "user_name": ["alice", "bob", "alice"],
            "host_name": ["host1", "host2", "host1"]
        })
        baseline = RelationshipFrequencyBaseline("user_name", "host_name")
        baseline.fit(data)

        assert baseline.state["known_pairs"] == {("alice", "host1"), ("bob", "host2")}

        # Test serialization
        serialized = baseline.to_dict()
        assert isinstance(serialized["known_pairs"], list)
        assert ["alice", "host1"] in serialized["known_pairs"]

        # Test deserialization
        new_baseline = RelationshipFrequencyBaseline("user_name", "host_name")
        new_baseline.from_dict(serialized)
        assert new_baseline.state["known_pairs"] == {("alice", "host1"), ("bob", "host2")}

    def test_feature_statistics_baseline(self) -> None:
        data = pa.table({
            "window_start": [datetime(2025, 7, 1, tzinfo=UTC)] * 3,
            "event_count": [10.0, 20.0, 30.0]
        })
        baseline = FeatureStatisticsBaseline("event_count")
        baseline.fit(data)

        assert baseline.state["min"] == 10.0
        assert baseline.state["max"] == 30.0
        assert baseline.mean == 20.0

    def test_temporal_statistics_baseline(self) -> None:
        data = pa.table({
            "window_start": [datetime(2025, 7, 1, tzinfo=UTC)] * 3,
            "hour_of_day": [14, 14, 2]
        })
        baseline = TemporalStatisticsBaseline()
        baseline.fit(data)

        assert baseline.state["events_per_hour"][14] == 2
        assert baseline.state["events_per_hour"][2] == 1
        assert baseline.state["events_per_hour"][0] == 0

        serialized = baseline.to_dict()
        assert serialized["events_per_hour"]["14"] == 2

        new_baseline = TemporalStatisticsBaseline()
        new_baseline.from_dict(serialized)
        assert new_baseline.state["events_per_hour"][14] == 2
