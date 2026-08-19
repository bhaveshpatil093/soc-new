"""
Validation gate: IP features.

Test internal/external classification against a small set of known internal and
known external IPs to confirm the range logic is correct, and confirm a genuinely
novel IP produces a distinct novelty signal without raising.
"""
from __future__ import annotations

from tads.features.ips import (
    UniqueSourceIPsFeature,
    UniqueDestinationIPsFeature,
    SourceIpConcentrationFeature,
    DestinationDiversityFeature,
    InternalExternalProportionFeature,
    IpUserDiversityFeature,
    IpHostDiversityFeature,
    HistoricalIpFrequencyFeature,
    RelationshipNoveltyFeature,
)

FEATURES = [
    UniqueSourceIPsFeature(),
    UniqueDestinationIPsFeature(),
    SourceIpConcentrationFeature(),
    DestinationDiversityFeature(),
    InternalExternalProportionFeature(),
    IpUserDiversityFeature(),
    IpHostDiversityFeature(),
    HistoricalIpFrequencyFeature(),
    RelationshipNoveltyFeature(),
]


def print_results(case_name: str, computed: dict[str, float]) -> None:
    print(f"\n--- {case_name} ---")
    for k, v in computed.items():
        print(f"  {k:<30} : {v:.4f}")


def main() -> None:
    print("=== Demo: IP Features Validation ===")

    # Baseline for novelty testing
    baseline = {
        "known_source_ips": {"10.0.0.1", "192.168.1.1"},
        "known_ip_user_pairs": {("10.0.0.1", "alice")},
    }

    # Test cases combining internal/external classification and novelty
    events = [
        # Internal, known, known relationship
        {"source_ip": "10.0.0.1", "user_name": "alice"},
        # Internal, known, NOVEL relationship
        {"source_ip": "192.168.1.1", "user_name": "bob"},
        # External, completely novel IP
        {"source_ip": "8.8.8.8", "user_name": "charlie"},
        # Invalid IP (should be ignored in internal/external ratio)
        {"source_ip": "invalid_gibberish", "user_name": "alice"},
    ]
    window_data = {"events": events, "baseline": baseline}
    
    computed = {}
    for feat in FEATURES:
        computed.update(feat.compute(window_data))
        
    print_results("IP Features Window", computed)

    # Validations
    assert computed["unique_source_ips"] == 4.0, "Should count 4 distinct IPs (including gibberish)."
    
    # Internal ratio: valid IPs are 10.0.0.1 (int), 192.168.1.1 (int), 8.8.8.8 (ext). Ratio = 2/3.
    assert abs(computed["internal_source_ratio"] - (2 / 3)) < 1e-6, "Internal ratio should be 2/3 (valid IPs only)."
    
    # Historical Deviation: 10.0.0.1 and 192.168.1.1 are known. 8.8.8.8 and 'invalid_gibberish' are unknown. Ratio = 2/4 = 0.5.
    assert computed["historical_ip_deviation"] == 0.5, "Deviation should be 0.5 (2 novel out of 4)."

    # Relationship Novelty: (10.0.0.1, alice) is known. The other 3 pairs are novel. Ratio = 3/4 = 0.75.
    assert computed["relationship_novelty_ip_user"] == 0.75, "Relationship novelty should be 0.75 (3 novel out of 4)."

    print("\nSUCCESS: Internal/External classification and novelty signals behave exactly as expected.")


if __name__ == "__main__":
    main()
