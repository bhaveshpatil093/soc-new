from datetime import UTC, datetime

import pyarrow as pa
import pytest

from tads.models.base import BaseModel, TemporalLeakageError


class TestTemporalLeakageEnforcement:
    """Tests the mechanical enforcement of the strict train/test temporal separation principle."""

    def test_fitting_with_august_data_raises_error(self) -> None:
        """
        Verify that passing August data to a model configured for July training
        raises a TemporalLeakageError, enforcing the 'No August in Training' rule.
        """
        # Model is strictly bound to July data (before August 1st)
        july_end_bound = datetime(2025, 8, 1, tzinfo=UTC)
        model = BaseModel(training_end_bound=july_end_bound)

        # Create a synthetic PyArrow table containing an August timestamp (Leakage!)
        leakage_data = pa.table({
            "timestamp": [
                datetime(2025, 7, 15, tzinfo=UTC),
                datetime(2025, 8, 2, tzinfo=UTC) # August data point
            ],
            "value": [1.0, 2.0]
        })

        # The mechanical enforcement should catch the August timestamp and raise an error
        with pytest.raises(TemporalLeakageError, match="Temporal leakage detected"):
            model.fit(leakage_data)

        assert not model.is_fitted, "Model should not be fitted if leakage is detected."

    def test_fitting_with_july_only_data_succeeds(self) -> None:
        """
        Verify that passing purely July data to the model succeeds.
        """
        july_end_bound = datetime(2025, 8, 1, tzinfo=UTC)
        model = BaseModel(training_end_bound=july_end_bound)

        # Pure July data
        valid_data = pa.table({
            "timestamp": [
                datetime(2025, 7, 1, tzinfo=UTC),
                datetime(2025, 7, 31, 23, 59, 59, tzinfo=UTC)
            ],
            "value": [1.0, 2.0]
        })

        # Should not raise any errors
        model.fit(valid_data)
        assert model.is_fitted, "Model should be successfully fitted with valid data."
