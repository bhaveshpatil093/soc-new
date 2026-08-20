"""
Validation gate: Benchmark entropy computation.
"""
from __future__ import annotations

import random
import time

from tads.features.utils import calculate_entropy


def main() -> None:
    print("=== Demo: Entropy Benchmark ===\n")

    # Simulate a very busy 5-second window: 10,000 events
    # with a high-cardinality distribution (e.g. 5,000 unique destination IPs)
    num_events = 10000
    num_unique = 5000

    events = [
        {"field": f"val_{random.randint(1, num_unique)}"}
        for _ in range(num_events)
    ]

    print(f"Dataset generated: {num_events} events, ~{num_unique} unique categories.")

    # Warmup
    _ = calculate_entropy(events, "field")

    num_iterations = 1000
    start_time = time.perf_counter()

    for _ in range(num_iterations):
        _ = calculate_entropy(events, "field")

    end_time = time.perf_counter()

    total_time = end_time - start_time
    time_per_window = (total_time / num_iterations) * 1000 # in ms

    print(f"Total time for {num_iterations} windows: {total_time:.4f} seconds")
    print(f"Average time per window (entropy calc): {time_per_window:.4f} ms")

    print("\nConclusion:")
    if time_per_window < 5.0:
        print("✅ The computational cost is a few milliseconds per busy window.")
        print("   It is an entirely negligible fraction of feature-computation time.")
    else:
        print("❌ The cost is unexpectedly high.")


if __name__ == "__main__":
    main()
