"""
Validation benchmark for Event Attribution.

Validates that high-evidence windows can be defensibly traced back to their
underlying raw events.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from tads.explanation.attribution import EventAttributor


def create_categorical_anomaly_window() -> tuple[list[dict], list[str]]:
    """Simulate a window with 20 events where one event contains an unseen user."""
    events = []
    base_ts = datetime(2025, 8, 1, 10, 0, 0, tzinfo=UTC)

    # 19 normal events
    for i in range(19):
        events.append({
            "_id": f"evt_cat_{i}",
            "@timestamp": f"{base_ts.isoformat()}",
            "user": "alice" if i % 2 == 0 else "bob",
            "event_category": "network",
            "bytes_sent": 100 * (i + 1),
            "dest_ip": f"192.168.1.{i}",
        })

    # 1 anomalous event
    events.append({
        "_id": "evt_cat_ANOMALY",
        "@timestamp": f"{base_ts.isoformat()}",
        "user": "HACKER_ADMIN",
        "event_category": "authentication",
        "bytes_sent": 45,
        "dest_ip": "10.0.0.5",
    })

    anomalous_features = ["Driven by user='HACKER_ADMIN' [UNSEEN]"]
    return events, anomalous_features


def create_distributional_anomaly_window() -> tuple[list[dict], list[str]]:
    """Simulate a window with a massive event count spike."""
    events = []
    base_ts = datetime(2025, 8, 1, 10, 5, 0, tzinfo=UTC)

    # 500 events simulating a volumetric burst
    for i in range(500):
        events.append({
            "_id": f"evt_vol_{i}",
            "@timestamp": f"{base_ts.isoformat()}",
            "user": "service-account",
            "event_category": "network",
            "bytes_sent": 5000,
            "dest_ip": "192.168.1.100",
        })

    anomalous_features = ["event_count"]
    return events, anomalous_features


def main() -> None:
    attributor = EventAttributor()

    print("="*80)
    print("=== SCENARIO 1: CATEGORICAL NOVELTY ANOMALY ===")
    print("="*80)

    cat_events, cat_features = create_categorical_anomaly_window()
    print(f"Total raw events in window: {len(cat_events)}")
    print(f"Anomalous features: {cat_features}")

    cat_attributed = attributor.attribute(cat_events, cat_features)

    print("\n--- Attributed Events ---")
    for ev in cat_attributed:
        print(f"Event ID:   {ev.event_id}")
        print(f"Method:     {ev.attribution_method}")
        print(f"Confidence: {ev.attribution_confidence}")
        print(f"Fields:     {json.dumps(ev.relevant_fields)}")
        print("-" * 40)

    print("\n" + "="*80)
    print("=== SCENARIO 2: DISTRIBUTIONAL BURST ANOMALY ===")
    print("="*80)

    vol_events, vol_features = create_distributional_anomaly_window()
    print(f"Total raw events in window: {len(vol_events)}")
    print(f"Anomalous features: {vol_features}")

    vol_attributed = attributor.attribute(vol_events, vol_features)

    print(f"\n--- Attributed Events (Showing first 3 of {len(vol_attributed)}) ---")
    for ev in vol_attributed[:3]:
        print(f"Event ID:   {ev.event_id}")
        print(f"Method:     {ev.attribution_method}")
        print(f"Confidence: {ev.attribution_confidence}")
        print(f"Fields:     {json.dumps(ev.relevant_fields)}")
        print("-" * 40)

    print(f"\n[Note: Total attributed capped at {len(vol_attributed)} to prevent memory explosion]")


if __name__ == "__main__":
    main()
