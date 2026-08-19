import pyarrow as pa
import pyarrow.compute as pc
from datetime import datetime, timezone

class TemporalLeakageError(Exception):
    """Raised when data from outside the allowed temporal window is passed to a function."""
    pass

def validate_training_data_temporal_bounds(data: pa.Table, max_allowed_timestamp: datetime):
    """
    Validates that no data in the training set exceeds the maximum allowed timestamp.
    Enforces the 'Strict Train/Test Separation' principle (No August data in training).
    """
    if "timestamp" not in data.column_names:
        raise ValueError("Data must contain a 'timestamp' column for temporal validation.")

    # Get the maximum timestamp in the dataset
    max_ts_in_data = pc.max(data.column("timestamp")).as_py()
    
    # Ensure it's timezone aware for comparison
    if max_ts_in_data.tzinfo is None:
        max_ts_in_data = max_ts_in_data.replace(tzinfo=timezone.utc)
        
    if max_allowed_timestamp.tzinfo is None:
        max_allowed_timestamp = max_allowed_timestamp.replace(tzinfo=timezone.utc)

    if max_ts_in_data >= max_allowed_timestamp:
        raise TemporalLeakageError(
            f"Temporal leakage detected! Found data with timestamp {max_ts_in_data}, "
            f"which is >= the maximum allowed training bound of {max_allowed_timestamp}."
        )

class BaseModel:
    """Base class for TADS models demonstrating temporal leakage prevention."""
    
    def __init__(self, training_end_bound: datetime):
        self.training_end_bound = training_end_bound
        self.is_fitted = False
        
    def fit(self, data: pa.Table):
        """Fits the model, strictly enforcing temporal bounds."""
        validate_training_data_temporal_bounds(data, self.training_end_bound)
        # Proceed with fitting...
        self.is_fitted = True
