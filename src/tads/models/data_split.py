"""
Utility for strictly enforcing the chronological dataset split for July.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

logger = logging.getLogger(__name__)


class JulyDatasetSplitter:
    """
    Enforces a strict chronological split of the July dataset.

    Training: July 1 to July 21 (inclusive). Used for fitting model weights.
    Validation: July 22 to July 31 (inclusive). Used for calibration and tuning.
    """

    TRAIN_END = datetime(2025, 7, 21, 23, 59, 59, tzinfo=UTC)
    VAL_START = datetime(2025, 7, 22, 0, 0, 0, tzinfo=UTC)
    VAL_END = datetime(2025, 7, 31, 23, 59, 59, tzinfo=UTC)

    @classmethod
    def split(cls, july_data: pa.Table) -> tuple[pa.Table, pa.Table]:
        """
        Split a PyArrow table containing July data into Train and Validation sets.

        Args:
            july_data: A PyArrow table containing a 'window_start' timestamp column.

        Returns:
            A tuple of (train_table, validation_table).
        """
        if "window_start" not in july_data.column_names:
            raise ValueError("Table must contain a 'window_start' column.")

        # Extract timestamp column
        window_starts = july_data.column("window_start")

        # Create boolean masks
        train_mask = pc.less_equal(window_starts, cls.TRAIN_END)
        val_mask = pc.and_(pc.greater_equal(window_starts, cls.VAL_START), pc.less_equal(window_starts, cls.VAL_END))

        # Filter tables
        train_table = july_data.filter(train_mask)
        val_table = july_data.filter(val_mask)

        logger.info(f"Split July dataset: {len(train_table)} train rows, {len(val_table)} validation rows.")

        return train_table, val_table
