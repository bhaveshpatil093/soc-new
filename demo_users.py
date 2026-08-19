"""
Validation gate: User features.

Run user features against a window containing at least one unseen-user case and
one all-known-users case, showing both complete without error and produce
sensible values.
"""
from __future__ import annotations

from tads.features.users import (
    ActiveUsersFeature,
    UserEventConcentrationFeature,
    UserDiversityFeature,
    LoginVolumeFeature,
    FailedLoginRatioFeature,
    UserHostDiversityFeature,
    UserIpDiversityFeature,
    UserProcessDiversityFeature,
    HistoricalUserDeviationFeature,
)

FEATURES = [
    ActiveUsersFeature(),
    UserEventConcentrationFeature(),
    UserDiversityFeature(),
    LoginVolumeFeature(),
    FailedLoginRatioFeature(),
    UserHostDiversityFeature(),
    UserIpDiversityFeature(),
    UserProcessDiversityFeature(),
    HistoricalUserDeviationFeature(),
]


def print_results(case_name: str, computed: dict[str, float]) -> None:
    print(f"\n--- {case_name} ---")
    for k, v in computed.items():
        print(f"  {k:<30} : {v:.4f}")


def main() -> None:
    print("=== Demo: User Features Validation ===")

    baseline = {"known_users": {"alice", "bob"}}

    # Case 1: All known users
    all_known_events = [
        {"user_name": "alice", "event_category": "authentication", "event_action": "logon", "event_outcome": "success", "host_name": "h1"},
        {"user_name": "bob", "event_category": "authentication", "event_action": "logon", "event_outcome": "failure", "source_ip": "10.0.0.1"},
        {"user_name": "alice", "process_name": "cmd.exe", "host_name": "h2"},
    ]
    window_data_known = {"events": all_known_events, "baseline": baseline}
    
    computed_known = {}
    for feat in FEATURES:
        computed_known.update(feat.compute(window_data_known))
        
    print_results("All-Known-Users Case", computed_known)
    assert computed_known["historical_user_deviation"] == 0.0, "Historical deviation should be 0.0 for all known users."
    assert computed_known["failed_login_ratio"] == 0.5, "Ratio should be 0.5 (1 failure out of 2 logons)."

    # Case 2: Unseen users
    unseen_events = [
        {"user_name": "charlie", "event_category": "network", "source_ip": "192.168.1.1"},
        {"user_name": "eve", "event_category": "process", "process_name": "malware.exe"},
        {"user_name": None, "event_category": "process", "process_name": "unknown.exe"},
    ]
    window_data_unseen = {"events": unseen_events, "baseline": baseline}
    
    computed_unseen = {}
    for feat in FEATURES:
        computed_unseen.update(feat.compute(window_data_unseen))
        
    print_results("Unseen-User Case", computed_unseen)
    assert computed_unseen["historical_user_deviation"] == 1.0, "Historical deviation should be 1.0 (100% novel events)."
    assert computed_unseen["active_users"] == 3.0, "Should be 3 active users (charlie, eve, unknown)."

    print("\nSUCCESS: User features handle both known and novel users gracefully.")


if __name__ == "__main__":
    main()
