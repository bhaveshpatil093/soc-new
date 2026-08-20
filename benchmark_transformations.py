"""
Validation gate for feature transformations.

Manually populates July baseline components, applies transformations to 
an "August" value, and asserts that the outputs match manual mathematical calculations.
"""

from __future__ import annotations

import math
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
from tads.baselines.frequencies import UserFrequencyBaseline
from tads.baselines.statistics import RobustFeatureStatisticsBaseline
from tads.transformations.categorical import FrequencyRarityTransformation
from tads.transformations.numeric import (
    IQRDistanceTransformation,
    PercentileRankTransformation,
    RobustZScoreTransformation,
    TailDistanceTransformation,
)


def validate_numeric_transformations() -> None:
    print("--- Validating Numeric Transformations ---")
    
    # 1. Setup a controlled July Baseline
    # Values: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    # Median = 5.5
    # MAD = 2.5
    # IQR = p75 (7.75) - p25 (3.25) = 4.5
    
    july_time = datetime(2025, 7, 15, tzinfo=UTC)
    data = pa.table({
        "window_start": [july_time] * 10,
        "test_feature": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    })
    
    baseline = RobustFeatureStatisticsBaseline(features=["test_feature"])
    baseline.fit(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        baseline.save(tmp_path, "stats")
        
        # Load frozen
        frozen_baseline = RobustFeatureStatisticsBaseline(features=["test_feature"])
        frozen_baseline.load(tmp_path, "stats")
        frozen_baseline.is_frozen = True
        
        stats = frozen_baseline.get_statistics("test_feature")
        print("Fitted July Statistics:")
        for k, v in stats.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")
                
        assert stats["median"] == 5.5
        assert stats["mad"] == 2.5
        
        # 2. Test Transformations with an "August" value
        august_value = 15.5
        
        # Robust Z-Score
        z_trans = RobustZScoreTransformation(frozen_baseline)
        z_score = z_trans.apply("test_feature", august_value)
        expected_z = (15.5 - 5.5) / 2.5
        print(f"\nRobust Z-Score for {august_value}: {z_score:.2f} (Expected: {expected_z:.2f})")
        assert math.isclose(z_score, expected_z)
        
        # IQR Distance
        iqr_trans = IQRDistanceTransformation(frozen_baseline, k=1.5)
        iqr_dist = iqr_trans.apply("test_feature", august_value)
        
        upper_bound = stats["p75"] + 1.5 * stats["iqr"]
        expected_iqr_dist = (august_value - upper_bound) / stats["iqr"]
        print(f"IQR Distance for {august_value}: {iqr_dist:.2f} (Expected: {expected_iqr_dist:.2f})")
        assert math.isclose(iqr_dist, expected_iqr_dist)
        
        # Percentile Rank (interpolation)
        pct_trans = PercentileRankTransformation(frozen_baseline)
        # Value exactly at p90
        p90_val = stats["p90"]
        pct_p90 = pct_trans.apply("test_feature", p90_val)
        print(f"Percentile Rank for {p90_val}: {pct_p90:.2f} (Expected: 0.90)")
        assert math.isclose(pct_p90, 0.90)
        
        # Value halfway between p50 (5.5) and p75 (7.75) => 6.625
        val_mid = (stats["median"] + stats["p75"]) / 2
        pct_mid = pct_trans.apply("test_feature", val_mid)
        # Expected rank is halfway between 0.50 and 0.75 => 0.625
        print(f"Percentile Rank for {val_mid:.3f}: {pct_mid:.3f} (Expected: 0.625)")
        assert math.isclose(pct_mid, 0.625)
        
        # Tail Distance
        tail_trans = TailDistanceTransformation(frozen_baseline)
        tail_dist = tail_trans.apply("test_feature", august_value)
        expected_tail = (august_value - stats["p99"]) / stats["iqr"]
        print(f"Tail Distance for {august_value}: {tail_dist:.2f} (Expected: {expected_tail:.2f})")
        assert math.isclose(tail_dist, expected_tail)


def validate_categorical_transformations() -> None:
    print("\n--- Validating Categorical Transformations ---")
    
    july_time = datetime(2025, 7, 15, tzinfo=UTC)
    data = pa.table({
        "window_start": [july_time] * 100,
        # user_A appears 90 times, user_B 10 times
        "user_name": ["user_A"] * 90 + ["user_B"] * 10
    })
    
    baseline = UserFrequencyBaseline()
    baseline.fit(data)
    
    frozen_baseline = UserFrequencyBaseline()
    frozen_baseline.from_dict(baseline.to_dict())
    frozen_baseline.is_frozen = True
    
    trans = FrequencyRarityTransformation(frozen_baseline, pseudocount=0.5)
    
    # Rarity of user_A (Common)
    rarity_a = trans.apply("user_A")
    expected_p_a = 90 / 100.5
    expected_rarity_a = -math.log10(expected_p_a)
    print(f"Rarity for common user_A: {rarity_a:.4f} (Expected: {expected_rarity_a:.4f})")
    assert math.isclose(rarity_a, expected_rarity_a)
    
    # Rarity of unseen user_C (August novelty)
    rarity_c = trans.apply("user_C")
    expected_p_c = 0.5 / 100.5
    expected_rarity_c = -math.log10(expected_p_c)
    print(f"Rarity for UNSEEN user_C: {rarity_c:.4f} (Expected: {expected_rarity_c:.4f})")
    assert math.isclose(rarity_c, expected_rarity_c)


if __name__ == "__main__":
    validate_numeric_transformations()
    validate_categorical_transformations()
