"""
Shared utilities for feature extraction.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Collection


def calculate_entropy(events: Collection[dict[str, Any]], field: str) -> float:
    """Calculate Shannon entropy for the distribution of a given field."""
    if not events:
        return 0.0
    counts = Counter(e.get(field) or "unknown" for e in events)
    if len(counts) <= 1:
        return 0.0
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((v / total) * math.log2(v / total) for v in counts.values())


def calculate_hhi(events: Collection[dict[str, Any]], field: str) -> float:
    """Calculate Herfindahl-Hirschman Index (HHI) for the distribution of a given field."""
    if not events:
        return 0.0
    counts = Counter(e.get(field) or "unknown" for e in events)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return sum((v / total) ** 2 for v in counts.values())


def average_distinct_per_entity(events: Collection[dict[str, Any]], entity_field: str, target_field: str) -> float:
    """Calculate average number of distinct `target_field` values per `entity_field`."""
    if not events:
        return 0.0

    entity_to_items: dict[str, set[str]] = {}
    for e in events:
        entity_val = e.get(entity_field) or "unknown"
        target_val = e.get(target_field) or "unknown"
        entity_to_items.setdefault(entity_val, set()).add(target_val)

    if not entity_to_items:
        return 0.0

    total_distinct = sum(len(items) for items in entity_to_items.values())
    return float(total_distinct / len(entity_to_items))


def calculate_historical_deviation(
    events: Collection[dict[str, Any]],
    entity_field: str,
    baseline: dict[str, Any],
    baseline_key: str,
) -> float:
    """
    Calculate historical deviation (novelty ratio) for an entity field.
    Returns the ratio of events where the entity is missing from the baseline.
    """
    if not events:
        return 0.0

    known_entities: set[str] = baseline.get(baseline_key, set())
    novel_events = 0

    for e in events:
        entity_val = e.get(entity_field) or "unknown"
        if entity_val not in known_entities:
            novel_events += 1

    return float(novel_events / len(events))


def calculate_relationship_novelty(
    events: Collection[dict[str, Any]],
    field_1: str,
    field_2: str,
    baseline: dict[str, Any],
    baseline_key: str,
) -> float:
    """
    Calculate relationship novelty ratio for pairs of entities.
    Returns the ratio of events where the pair (field_1, field_2) is missing from the baseline.
    """
    if not events:
        return 0.0

    known_pairs: set[tuple[str, str]] = baseline.get(baseline_key, set())
    novel_events = 0

    for e in events:
        val_1 = e.get(field_1) or "unknown"
        val_2 = e.get(field_2) or "unknown"
        if (val_1, val_2) not in known_pairs:
            novel_events += 1

    return float(novel_events / len(events))
