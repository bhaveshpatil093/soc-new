"""
Tests for the BaseAnomalyDetector interface and exact serialization round-tripping.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pytest

from tads.baselines.base import ImmutableBaselineError, TemporalLeakageError
from tads.models.detectors.base import BaseAnomalyDetector


class DummyEventCountDetector(BaseAnomalyDetector):  # type: ignore[misc]
    """
    Trivial detector for validation gate.
    Learns the max event_count in July.
    Scores based on raw event_count.
    Calibrates by dividing by July max.
    Flags anomaly if calibrated > threshold.
    """

    def _fit(self, data: pa.Table) -> None:
        if "event_count" not in data.column_names:
            self.state["max_events"] = 1.0
            return

        max_val = pc.max(data.column("event_count")).as_py()
        self.state["max_events"] = max_val if max_val is not None else 1.0

    def score(self, data: pa.Table) -> pa.Array:
        if "event_count" not in data.column_names:
            return pa.array([0.0] * len(data))
        return data.column("event_count")

    def _calibrate(self, raw_scores: pa.Array) -> pa.Array:
        max_events = self.state.get("max_events", 1.0)
        if max_events == 0:
            max_events = 1.0
        # calibrated = raw_score / max_events
        return pc.divide(raw_scores, max_events)

    def explain(self, data: pa.Table) -> pa.Array:
        return pa.array([f"Checked event count against max {self.state.get('max_events')}"] * len(data))


def test_detector_temporal_guard() -> None:
    """Test that the prompt 36 temporal guard strictly prevents August data."""
    detector = DummyEventCountDetector()

    july_data = pa.table({
        "window_start": [datetime(2025, 7, 31, 23, 59, 59, tzinfo=UTC)],
        "event_count": [10.0]
    })

    august_data = pa.table({
        "window_start": [datetime(2025, 8, 1, 0, 0, 1, tzinfo=UTC)],
        "event_count": [10.0]
    })

    # Should succeed
    detector.fit(july_data)
    assert detector.is_fitted
    assert detector.state["max_events"] == 10.0

    # Refitting a frozen detector should fail
    with pytest.raises(ImmutableBaselineError):
        detector.fit(july_data)

    # Fitting a fresh detector with August data should hard-crash
    fresh_detector = DummyEventCountDetector()
    with pytest.raises(TemporalLeakageError, match="Temporal leakage detected"):
        fresh_detector.fit(august_data)


def test_detector_roundtrip_and_predict() -> None:
    """
    Test that the exact mathematical output matches before and after
    save/load serialization round-tripping.
    """
    july_data = pa.table({
        "window_start": [datetime(2025, 7, 15, tzinfo=UTC)],
        "event_count": [100.0]  # Max July events = 100
    })

    august_data = pa.table({
        "window_start": [datetime(2025, 8, 15, tzinfo=UTC)] * 3,
        "event_count": [50.0, 100.0, 150.0]
    })

    # 1. Train Original
    detector = DummyEventCountDetector(threshold=1.1)  # Anomaly if > 110% of July Max
    detector.fit(july_data)

    # 2. Predict Original
    orig_preds = detector.predict(august_data)

    assert orig_preds.column("raw_score").to_pylist() == [50.0, 100.0, 150.0]
    assert orig_preds.column("calibrated_evidence").to_pylist() == [0.5, 1.0, 1.5]
    assert orig_preds.column("anomaly").to_pylist() == [False, False, True]
    assert orig_preds.column("model_version").to_pylist() == ["v1.0"] * 3

    # 3. Save/Load Roundtrip
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "model.json"
        detector.save(tmp_path)

        loaded_detector = DummyEventCountDetector(threshold=999.0) # threshold should be overwritten by load
        loaded_detector.load(tmp_path)

    # 4. Assert State
    assert loaded_detector.is_fitted
    assert loaded_detector.threshold == 1.1
    assert loaded_detector.state["max_events"] == 100.0

    # 5. Predict Loaded and Compare
    loaded_preds = loaded_detector.predict(august_data)

    assert orig_preds.equals(loaded_preds), "Loaded predictions mathematically diverged from original!"
