"""
Validation gate: Command-line pattern normalization.

Confirms that command lines differing only by volatile arguments (e.g. PIDs,
temp file paths, IPs, UUIDs) normalize to identical structural patterns,
while genuinely different commands normalize differently.
"""
from __future__ import annotations

from tads.features.processes import normalize_cmdline


def main() -> None:
    print("=== Demo: Command-Line Pattern Normalization ===\n")

    # Group 1: Differing only by PID and Temp File Name
    group1 = [
        r"C:\Windows\System32\cmd.exe /c start /wait proc.exe --pid 1234 --out C:\Temp\foo_123.txt",
        r"c:\windows\system32\cmd.exe /c start /wait proc.exe --pid 5678 --out C:\Temp\bar_456.txt",
    ]
    
    # Group 2: Network tools differing by IP and UUID
    group2 = [
        "ping.exe 192.168.1.1 -n 4 --session 550e8400-e29b-41d4-a716-446655440000",
        "ping.exe 10.0.0.5 -n 4 --session 123e4567-e89b-12d3-a456-426614174000",
    ]
    
    # Group 3: Generic script execution differing by timestamp and hash
    group3 = [
        "python.exe run_job.py --ts 1692345678 --hash a1b2c3d4e5f67890",
        "python.exe run_job.py --ts 1692345999 --hash 0987654321fedcba",
    ]
    
    # Genuinely different command
    different = "python.exe run_cleanup.py --force"

    all_groups = [
        ("Group 1 (PIDs & Temp Files)", group1),
        ("Group 2 (IPs & UUIDs)", group2),
        ("Group 3 (Timestamps & Hashes)", group3),
    ]

    for group_name, cmds in all_groups:
        print(f"--- {group_name} ---")
        normalized_set = set()
        for cmd in cmds:
            norm = normalize_cmdline(cmd)
            normalized_set.add(norm)
            print(f"  Raw:  {cmd}")
            print(f"  Norm: {norm}\n")
            
        assert len(normalized_set) == 1, f"Commands in {group_name} did not normalize to the same pattern!"
        print(f"✅ {group_name} successfully normalized to a single pattern.\n")

    print("--- Genuinely Different Command ---")
    norm_diff = normalize_cmdline(different)
    print(f"  Raw:  {different}")
    print(f"  Norm: {norm_diff}\n")
    
    # Verify the different command doesn't match Group 3
    norm_g3 = normalize_cmdline(group3[0])
    assert norm_diff != norm_g3, "Genuinely different command incorrectly matched the other pattern!"
    print("✅ Genuinely different command produced a distinct pattern.\n")
    
    print("SUCCESS: Command-line normalizer behaves exactly as expected.")


if __name__ == "__main__":
    main()
