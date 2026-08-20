"""
Validation gate: Cross-check IP features and Network features for consistency.

Confirms that overlapping concepts (like Unique Destination IPs) compute
to exactly the same value when run from the IP module and the Network module.
"""
from __future__ import annotations

from tads.features.ips import UniqueDestinationIPsFeature
from tads.features.network import NetworkUniqueDestinationsFeature


def main() -> None:
    print("=== Demo: IP vs Network Feature Consistency ===\n")

    # Sample window of data containing destination IPs
    events = [
        {"destination_ip": "1.1.1.1"},
        {"destination_ip": "8.8.8.8"},
        {"destination_ip": "1.1.1.1"},
        {"destination_ip": "10.0.0.5"},
        {"destination_ip": None}, # Missing should be handled identically
    ]
    
    window = {"events": events}

    # Initialize both features
    ip_feat = UniqueDestinationIPsFeature()
    net_feat = NetworkUniqueDestinationsFeature()
    
    # Compute
    ip_result = ip_feat.compute(window)
    net_result = net_feat.compute(window)
    
    print(f"IP Feature Result:      {ip_result}")
    print(f"Network Feature Result: {net_result}")
    
    val_ip = ip_result["unique_destination_ips"]
    val_net = net_result["network_unique_destinations"]
    
    # Assert they agree exactly
    assert val_ip == val_net, f"Mismatch! IP: {val_ip}, Network: {val_net}"
    
    print("\n✅ Consistency Check Passed: Both features share identical underlying logic and produce the exact same metric value.")


if __name__ == "__main__":
    main()
