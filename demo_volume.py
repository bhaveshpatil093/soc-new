"""
Validation gate: Volume features.

Computes volume features on a small hand-verifiable sample window and manually
confirms each value against a direct count of the raw events.
"""
from __future__ import annotations

from tads.features.volume import (
    ActionCountsFeature,
    AuthenticationVolumeFeature,
    CategoryCountsFeature,
    EventCountFeature,
    EventsPerSecondFeature,
    FileActivityVolumeFeature,
    NetworkVolumeFeature,
    OutcomeCountsFeature,
    ProcessVolumeFeature,
)


def main() -> None:
    print("=== Demo: Volume Features Validation ===")

    # 1. Define a hand-verifiable set of 10 events
    sample_events = [
        # Network
        {"event_category": "network", "event_action": "allowed", "event_outcome": "success"},
        {"event_category": "network", "event_action": "denied", "event_outcome": "failure"},
        {"event_category": "network", "event_action": "allowed", "event_outcome": "success"},
        # Auth
        {"event_category": "authentication", "event_action": "logon", "event_outcome": "success"},
        {"event_category": "authentication", "event_action": "logon", "event_outcome": "failure"},
        # Process
        {"event_category": "process", "event_action": "created", "event_outcome": "success"},
        {"event_category": "process", "event_action": "terminated", "event_outcome": "success"},
        {"event_category": "process", "event_action": "created", "event_outcome": "success"},
        # File
        {"event_category": "file", "event_action": "read", "event_outcome": "success"},
        # Unknown/Nulls
        {"event_category": None, "event_action": None, "event_outcome": None},
    ]

    window_data = {"events": sample_events}

    # 2. Directly compute the true counts manually
    expected = {
        "event_count": 10.0,
        "events_per_second": 2.0,
        "category_count_network": 3.0,
        "category_count_authentication": 2.0,
        "category_count_process": 3.0,
        "category_count_file": 1.0,
        "category_count_unknown": 1.0,
        "action_count_allowed": 2.0,
        "action_count_denied": 1.0,
        "action_count_logon": 2.0,
        "action_count_created": 2.0,
        "action_count_terminated": 1.0,
        "action_count_read": 1.0,
        "action_count_unknown": 1.0,
        "outcome_count_success": 7.0,
        "outcome_count_failure": 2.0,
        "outcome_count_unknown": 1.0,
        "authentication_volume": 2.0,
        "network_volume": 3.0,
        "process_volume": 3.0,
        "file_activity_volume": 1.0,
    }

    # 3. Compute using the features
    features = [
        EventCountFeature(),
        EventsPerSecondFeature(),
        CategoryCountsFeature(),
        ActionCountsFeature(),
        OutcomeCountsFeature(),
        AuthenticationVolumeFeature(),
        NetworkVolumeFeature(),
        ProcessVolumeFeature(),
        FileActivityVolumeFeature(),
    ]

    computed = {}
    for feat in features:
        computed.update(feat.compute(window_data))

    # 4. Compare and print
    success = True
    print("\nValidating computed features against hand-counted expectations:")
    for k, v_exp in expected.items():
        v_comp = computed.get(k, 0.0)
        match = "✅" if v_exp == v_comp else "❌"
        if v_exp != v_comp:
            success = False
        print(f"  {k:<30} | Expected: {v_exp:<4} | Computed: {v_comp:<4} {match}")

    print("\nOverall Status: " + ("SUCCESS" if success else "FAILED"))
    assert success, "One or more features did not match expectations."


if __name__ == "__main__":
    main()
