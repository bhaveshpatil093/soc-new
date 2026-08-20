"""
Numeric Transformations.

Map raw August numeric features into normalized anomaly scores based on robust
statistics from the July baseline.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from tads.transformations.base import BaseTransformation

if TYPE_CHECKING:
    from tads.baselines.statistics import RobustFeatureStatisticsBaseline


class RobustZScoreTransformation(BaseTransformation):  # type: ignore[misc]
    """
    Computes a robust Z-score using Median and MAD instead of Mean and StdDev.
    Score = (Value - Median) / MAD
    """

    def __init__(self, baseline: RobustFeatureStatisticsBaseline) -> None:
        super().__init__(baseline)

    def apply(self, feature_name: str, value: float) -> float:
        stats = self.baseline.get_statistics(feature_name)
        if not stats:
            return 0.0  # Unseen feature, no anomaly signal

        median = stats["median"]
        mad = stats["mad"]

        if mad > 0:
            return (value - median) / mad

        # Fallback if MAD is 0 (constant baseline).
        # If std > 0, we can use std (though highly unlikely if MAD is 0 unless heavily spiked).
        # Otherwise, any deviation from the constant median is an anomaly.
        std = stats["std"]
        if std > 0:
            return (value - median) / std

        # Complete constant
        return float(value - median)


class IQRDistanceTransformation(BaseTransformation):  # type: ignore[misc]
    """
    Measures how far outside the standard IQR bounds [Q1 - 1.5*IQR, Q3 + 1.5*IQR] a value is.
    Returns 0 if within bounds. Returns distance in IQR units if outside.
    """

    def __init__(self, baseline: RobustFeatureStatisticsBaseline, k: float = 1.5) -> None:
        super().__init__(baseline)
        self.k = k

    def apply(self, feature_name: str, value: float) -> float:
        stats = self.baseline.get_statistics(feature_name)
        if not stats:
            return 0.0

        p25 = stats["p25"]
        p75 = stats["p75"]
        iqr = stats["iqr"]

        lower_bound = p25 - (self.k * iqr)
        upper_bound = p75 + (self.k * iqr)

        # Avoid division by zero
        scale = iqr if iqr > 0 else 1.0

        if value > upper_bound:
            return (value - upper_bound) / scale
        elif value < lower_bound:
            return (lower_bound - value) / scale

        return 0.0


class TailDistanceTransformation(BaseTransformation):  # type: ignore[misc]
    """
    Measures how far into the extreme tail (above p99) a value is,
    normalized by the IQR.
    """

    def __init__(self, baseline: RobustFeatureStatisticsBaseline) -> None:
        super().__init__(baseline)

    def apply(self, feature_name: str, value: float) -> float:
        stats = self.baseline.get_statistics(feature_name)
        if not stats:
            return 0.0

        p99 = stats["p99"]
        iqr = stats["iqr"]

        if value <= p99:
            return 0.0

        scale = iqr if iqr > 0 else 1.0
        return (value - p99) / scale


class PercentileRankTransformation(BaseTransformation):  # type: ignore[misc]
    """
    Estimates the percentile rank [0.0, 1.0] of a value based on the July baseline quantiles.
    Uses linear interpolation between known quantiles.
    """

    def __init__(self, baseline: RobustFeatureStatisticsBaseline) -> None:
        super().__init__(baseline)

    def apply(self, feature_name: str, value: float) -> float:
        stats = self.baseline.get_statistics(feature_name)
        if not stats:
            return 0.5  # Unknown distribution, return median guess

        # Known quantiles
        q_points = [
            (0.25, stats["p25"]),
            (0.50, stats["median"]),
            (0.75, stats["p75"]),
            (0.90, stats["p90"]),
            (0.95, stats["p95"]),
            (0.99, stats["p99"]),
            (0.999, stats["p99_9"])
        ]

        # Below p25
        if value <= q_points[0][1]:
            # We don't have minimum, assume 0 is min (common for telemetry)
            if value <= 0:
                return 0.0
            return 0.25 * (value / q_points[0][1]) if q_points[0][1] > 0 else 0.25

        # Above p99.9
        if value >= q_points[-1][1]:
            # Asymptotic approach to 1.0
            diff = value - q_points[-1][1]
            scale = stats["mad"] if stats["mad"] > 0 else 1.0
            return min(1.0, 0.999 + 0.001 * (1.0 - math.exp(-diff / scale)))

        # Interpolate between points
        for i in range(len(q_points) - 1):
            p_low, v_low = q_points[i]
            p_high, v_high = q_points[i+1]

            if v_low <= value <= v_high:
                if v_high == v_low:
                    return p_high
                ratio = (value - v_low) / (v_high - v_low)
                return p_low + ratio * (p_high - p_low)

        return 0.5
