"""
Test: Window boundary correctness (Constraint #7)
Test: Constants integrity

Verifies that the windowing constants are correctly defined
and that the 5-second window calculation produces expected results.
"""

from __future__ import annotations

import datetime

from tads.constants import (
    DEFAULT_SEED,
    FORBIDDEN_DATA_FORMATS,
    FORBIDDEN_NORMALIZATION_SOURCES,
    HASH_ALGORITHM,
    NUMERICAL_TOLERANCE,
    PARQUET_COMPRESSION,
    VALID_NORMALIZATION_SOURCES,
    WINDOW_SIZE_MS,
    WINDOW_SIZE_SECONDS,
)


class TestWindowConstants:
    """Verify window size constants."""

    def test_window_size_is_5_seconds(self) -> None:
        """Constraint #7: primary temporal unit = 5 seconds."""
        assert WINDOW_SIZE_SECONDS == 5

    def test_window_size_ms_consistent(self) -> None:
        """Millisecond constant must equal seconds * 1000."""
        assert WINDOW_SIZE_MS == WINDOW_SIZE_SECONDS * 1000
        assert WINDOW_SIZE_MS == 5000

    def test_window_id_calculation(self) -> None:
        """Window ID = floor(timestamp_epoch_ms / 5000) produces correct assignments."""
        # Timestamp at exactly a window boundary
        ts_ms = 1720000000000  # Some epoch millisecond timestamp
        window_id = ts_ms // WINDOW_SIZE_MS
        # Same window for +1ms, +4999ms
        assert (ts_ms + 1) // WINDOW_SIZE_MS == window_id
        assert (ts_ms + 4999) // WINDOW_SIZE_MS == window_id
        # Next window for +5000ms
        assert (ts_ms + 5000) // WINDOW_SIZE_MS == window_id + 1

    def test_events_at_boundary_go_to_next_window(self) -> None:
        """An event at exactly window_start + 5000ms belongs to the next window."""
        ts_ms = 1720000005000  # Exactly 5 seconds after 1720000000000
        window_1 = 1720000000000 // WINDOW_SIZE_MS
        window_2 = ts_ms // WINDOW_SIZE_MS
        assert window_2 == window_1 + 1


class TestNormalizationConstants:
    """Verify normalization constraint constants (Constraint #12)."""

    def test_only_training_is_valid_source(self) -> None:
        """Only 'training' is a valid normalization source."""
        assert VALID_NORMALIZATION_SOURCES == frozenset({"training"})

    def test_batch_is_forbidden(self) -> None:
        """'batch' normalization is explicitly forbidden."""
        assert "batch" in FORBIDDEN_NORMALIZATION_SOURCES

    def test_evaluation_is_forbidden(self) -> None:
        """'evaluation' normalization is explicitly forbidden."""
        assert "evaluation" in FORBIDDEN_NORMALIZATION_SOURCES


class TestDataFormatConstants:
    """Verify data format constraints (Constraint #16)."""

    def test_csv_is_forbidden(self) -> None:
        assert "csv" in FORBIDDEN_DATA_FORMATS

    def test_parquet_compression_defined(self) -> None:
        assert PARQUET_COMPRESSION == "zstd"


class TestReproducibilityConstants:
    """Verify reproducibility constants (Constraint #20)."""

    def test_default_seed_is_deterministic(self) -> None:
        assert isinstance(DEFAULT_SEED, int)
        assert DEFAULT_SEED == 42

    def test_hash_algorithm(self) -> None:
        assert HASH_ALGORITHM == "sha256"

    def test_numerical_tolerance(self) -> None:
        assert NUMERICAL_TOLERANCE == 1e-6
        assert NUMERICAL_TOLERANCE > 0
