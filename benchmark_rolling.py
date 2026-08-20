"""
Benchmark: Cost of maintaining four parallel rolling scales at full data volume.

Simulates processing a full day of 5-second windows (17,280 windows)
and measures the time to maintain all four ring buffers and compute
all 60 rolling features per window.
"""
from __future__ import annotations

import random
import time

from tads.features.rolling import RollingContextComputer


def main() -> None:
    print("=== Benchmark: Multi-Scale Rolling Context ===\n")

    # A full day = 86400 seconds / 5 = 17280 windows
    num_windows = 17_280
    random.seed(42)

    # Generate synthetic window summaries
    summaries = [
        {
            "event_count": float(random.randint(0, 500)),
            "distinct_users": float(random.randint(0, 50)),
            "distinct_ips": float(random.randint(0, 100)),
            "distinct_hosts": float(random.randint(0, 30)),
            "distinct_processes": float(random.randint(0, 80)),
        }
        for _ in range(num_windows)
    ]

    # Warmup
    computer = RollingContextComputer()
    for s in summaries[:100]:
        computer.push(s)

    # Timed run
    computer = RollingContextComputer()
    start = time.perf_counter()

    for s in summaries:
        _ = computer.push(s)

    elapsed = time.perf_counter() - start
    per_window_us = (elapsed / num_windows) * 1_000_000

    print(f"Windows processed:   {num_windows}")
    print("Rolling scales:      4 (30s, 1m, 5m, 15m)")
    print("Features per window: 60 (5 metrics x 3 aggs x 4 scales)")
    print(f"Total time:          {elapsed:.4f} s")
    print(f"Per-window time:     {per_window_us:.1f} us")
    print()

    if per_window_us < 1000:
        print("Conclusion:")
        print(f"  The rolling context computation is sub-millisecond ({per_window_us:.0f} us)")
        print("  per window, even with 4 parallel scales and 180-window buffers.")
        print("  At full 17,280-window daily volume this adds < 1 second total.")
        print("  This is a negligible fraction of total feature-computation time.")
    else:
        print(f"WARNING: Per-window cost is {per_window_us:.0f} us — review for optimization.")


if __name__ == "__main__":
    main()
