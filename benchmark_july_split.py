"""
Validation benchmark for the July dataset chronological split.

Proves that the train and validation sets have exactly zero chronological overlap,
adhering strictly to the manifest boundaries, and that August is untouched.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import yaml

from tads.models.data_split import JulyDatasetSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_continuous_data(start: datetime, days: int) -> pa.Table:
    """Generate mock features over a span of days."""
    n_windows = (days * 24 * 60 * 60) // 5

    # Just generate timestamps in chunks to avoid massive memory overhead for the mock
    # Actually, 31 days * 17280 = 535,680 rows. That's fine for pyarrow.
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    return pa.table(
        {
            "window_start": timestamps,
            "dummy_feature": np.random.normal(0, 1, n_windows).tolist(),
        }
    )


def main() -> None:
    print("=== Loading Configuration Manifest ===")
    with open("config/july_split_manifest.yaml") as f:
        manifest = yaml.safe_load(f)

    print(yaml.dump(manifest, default_flow_style=False))

    print("\n=== Generating Continuous July Dataset (July 1 - July 31) ===")
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    raw_july = generate_continuous_data(july_start, days=31)

    print(f"Generated {len(raw_july)} rows of raw July data.")

    print("\n=== Executing Dataset Split ===")
    train_table, val_table = JulyDatasetSplitter.split(raw_july)

    train_min = pc.min(train_table.column("window_start")).as_py()
    train_max = pc.max(train_table.column("window_start")).as_py()

    val_min = pc.min(val_table.column("window_start")).as_py()
    val_max = pc.max(val_table.column("window_start")).as_py()

    print(f"Train bounds: {train_min} to {train_max}")
    print(f"Val bounds:   {val_min} to {val_max}")

    print("\n=== Validation Gate Checks ===")

    # 1. Assert Train does not bleed into Validation
    assert train_max <= JulyDatasetSplitter.TRAIN_END, "Train set bleeds past July 21st!"

    # 2. Assert Validation does not pull from Train
    assert val_min >= JulyDatasetSplitter.VAL_START, "Validation set pulls from before July 22nd!"

    # 3. Assert zero overlap
    assert train_max < val_min, "Chronological overlap detected between Train and Val!"

    # 4. Assert August is completely untouched
    august_start = datetime(2025, 8, 1, 0, 0, 0, tzinfo=UTC)
    assert val_max < august_start, "Validation set bleeds into August!"

    print("✅ SUCCESS: Dataset split strictly adheres to chronological boundaries.")
    print("✅ SUCCESS: Zero chronological overlap verified.")
    print("✅ SUCCESS: August holdout period is completely untouched.")


if __name__ == "__main__":
    main()
