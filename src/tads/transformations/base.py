"""
Base module for Transformations.

Transformations map raw August feature values into normalized anomaly scores based
strictly on frozen July baseline artifacts. They are structurally incapable of fitting
or mutating the baselines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tads.baselines.base import BaseBaseline


class BaseTransformation(ABC):
    """
    Abstract base class for all feature transformations.

    Transformations are initialized with a strictly frozen baseline component.
    They expose only an `apply()` method, ensuring no data leakage can occur
    from the evaluation period (August) back into the training state (July).
    """

    def __init__(self, baseline: BaseBaseline) -> None:
        if not getattr(baseline, "is_frozen", False):
            raise ValueError(
                "Transformations can only be initialized with a strictly frozen baseline."
            )
        self.baseline = baseline

    @abstractmethod
    def apply(self, *args: Any, **kwargs: Any) -> float:
        """
        Map a raw feature value(s) into a normalized score.
        Must be implemented by subclasses.
        """
        pass
