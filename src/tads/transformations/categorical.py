"""
Categorical/Frequency Transformations.

Map raw August categorical features (or entity relationships) into normalized
anomaly scores based on the July frequency baselines.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from tads.transformations.base import BaseTransformation

if TYPE_CHECKING:
    from tads.baselines.frequencies import DuckDBFrequencyBaseline, InMemoryFrequencyBaseline


class FrequencyRarityTransformation(BaseTransformation):  # type: ignore[misc]
    """
    Computes a rarity score for an entity or relationship based on its July baseline frequency.
    Score = -log10( P(entity) ).

    If an entity is completely unseen in July, it is assigned a pseudocount (e.g. 0.5)
    so it receives a highly anomalous, but mathematically stable, score.
    """

    def __init__(
        self,
        baseline: InMemoryFrequencyBaseline | DuckDBFrequencyBaseline,
        pseudocount: float = 0.5
    ) -> None:
        super().__init__(baseline)
        self.pseudocount = pseudocount

        # Cache total count to avoid repeated summation queries during inference
        # Duck-typing: Both baselines must expose get_total_count()
        self._total_count = float(self.baseline.get_total_count())

    def apply(self, *key_vals: str) -> float:
        """
        Pass the components of the relationship (e.g. user_name, source_ip).
        Returns the rarity score.
        """
        # Baseline get_frequency returns exact counts
        count = self.baseline.get_frequency(*key_vals)

        if count == 0:
            count = self.pseudocount

        total = self._total_count
        if total == 0:
            # Baseline is empty, cannot compute probabilities
            return 0.0

        # P(x) = count / total
        # Rarity = -log10(P(x))
        p = count / (total + self.pseudocount)
        return -math.log10(p)
