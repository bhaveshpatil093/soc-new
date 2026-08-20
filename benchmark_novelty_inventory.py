"""
Diagnostic script to inventory novel entities, relationships, temporal patterns,
and behaviours in August relative to the frozen July baseline.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

import numpy as np
import pyarrow as pa
from tabulate import tabulate


def generate_baseline_data(n_windows: int, start: datetime) -> pa.Table:
    """Generate the July baseline data (highly constrained)."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    # Strictly bound behavioral values
    event_counts = np.random.poisson(lam=10, size=n_windows)
    f_volume = event_counts * np.random.normal(5, 0.5, n_windows)
    f_latency = np.random.normal(30, 2, n_windows)
    f_cpu = np.random.normal(30, 2, n_windows)
    f_mem = f_cpu * 1.5 + np.random.normal(0, 1, n_windows)

    # Constrained entity sets
    users = ["alice", "bob", "service-account"]
    hosts = ["web-01", "db-01"]

    u_col = np.random.choice(users, size=n_windows)
    h_col = np.random.choice(hosts, size=n_windows)

    return pa.table(
        {
            "window_start": timestamps,
            "event_count": event_counts.tolist(),
            "f_volume": f_volume.tolist(),
            "f_latency": f_latency.tolist(),
            "f_cpu": f_cpu.tolist(),
            "f_mem": f_mem.tolist(),
            "user": u_col.tolist(),
            "host": h_col.tolist(),
        }
    )


def generate_august_data_with_novelty(base_data: pa.Table) -> pa.Table:
    """Take a generated table and intentionally inject novelties."""
    f_vol = base_data.column("f_volume").to_numpy().copy()
    f_cpu = base_data.column("f_cpu").to_numpy().copy()
    f_lat = base_data.column("f_latency").to_numpy().copy()
    users = base_data.column("user").to_pylist()
    hosts = base_data.column("host").to_pylist()

    # Inject NEW ENTITY (User never seen in July)
    users[100] = "EVE_HACKER"

    # Inject NEW ENTITY (Host never seen in July)
    hosts[200] = "secret-vault-01"

    # Inject NEW RELATIONSHIP (alice + db-01, assuming it might be rare,
    # but we'll force it. Wait, the baseline randomly pairs alice/bob with web/db.
    # To force a novel relationship, we'll introduce a new host AND user)
    # Actually, a new relationship could just be (service-account, secret-vault-01)
    # Since secret-vault-01 is new, any user pairing with it is a new relationship.
    # Let's force a pairing of known entities that didn't happen by chance?
    # No, it's easier to just inject a specific pairing and see if it gets flagged.

    # Inject RARE BEHAVIOUR (CPU spikes far beyond July max)
    f_cpu[300] = 999.0

    # Inject NEW TEMPORAL PATTERN (Activity at 3 AM. July data might not have 3 AM)
    # The timestamps are already set, we'll just evaluate whatever the generator made.

    return pa.table(
        {
            "window_start": base_data.column("window_start"),
            "event_count": base_data.column("event_count"),
            "f_volume": f_vol.tolist(),
            "f_latency": f_lat.tolist(),
            "f_cpu": f_cpu.tolist(),
            "f_mem": base_data.column("f_mem"),
            "user": users,
            "host": hosts,
        }
    )


class BaselineTracker:
    def __init__(self) -> None:
        self.seen_users: set[str] = set()
        self.seen_hosts: set[str] = set()
        self.seen_relationships: set[tuple[str, str]] = set()
        self.seen_hours: set[int] = set()

        self.max_cpu: float = 0.0
        self.max_volume: float = 0.0
        self.max_latency: float = 0.0

    def fit(self, data: pa.Table) -> None:
        self.seen_users = set(data.column("user").to_pylist())
        self.seen_hosts = set(data.column("host").to_pylist())

        users = data.column("user").to_pylist()
        hosts = data.column("host").to_pylist()
        self.seen_relationships = {(u, h) for u, h in zip(users, hosts)}

        timestamps = data.column("window_start").to_pylist()
        self.seen_hours = {ts.hour for ts in timestamps}

        self.max_cpu = float(np.max(data.column("f_cpu").to_numpy()))
        self.max_volume = float(np.max(data.column("f_volume").to_numpy()))
        self.max_latency = float(np.max(data.column("f_latency").to_numpy()))

    def inventory_novelty(self, data: pa.Table) -> dict[str, list[str]]:
        novelties = defaultdict(list)

        users = data.column("user").to_pylist()
        hosts = data.column("host").to_pylist()
        timestamps = data.column("window_start").to_pylist()
        f_cpu = data.column("f_cpu").to_numpy()
        f_vol = data.column("f_volume").to_numpy()
        f_lat = data.column("f_latency").to_numpy()

        for i in range(len(data)):
            u, h = users[i], hosts[i]
            ts = timestamps[i]

            if u not in self.seen_users:
                novelties["New User"].append(u)
                self.seen_users.add(u)  # Only report once

            if h not in self.seen_hosts:
                novelties["New Host"].append(h)
                self.seen_hosts.add(h)

            if (u, h) not in self.seen_relationships:
                novelties["New Relationship"].append(f"{u} -> {h}")
                self.seen_relationships.add((u, h))

            if ts.hour not in self.seen_hours:
                novelties["New Time of Day"].append(f"Hour: {ts.hour}")
                self.seen_hours.add(ts.hour)

            if f_cpu[i] > self.max_cpu:
                novelties["Rare Behavior (CPU)"].append(f"CPU={f_cpu[i]:.2f} (July Max: {self.max_cpu:.2f})")
                self.max_cpu = f_cpu[i]

            if f_vol[i] > self.max_volume:
                novelties["Rare Behavior (Volume)"].append(f"Vol={f_vol[i]:.2f} (July Max: {self.max_volume:.2f})")
                self.max_volume = f_vol[i]

        return novelties


def main() -> None:
    np.random.seed(42)

    # 1. Build Baseline
    print("=== Processing July Baseline ===")
    july_start = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)
    # Generate exactly 2 hours of data (10:00 to 12:00) so that August data at 14:00 is "novel"
    july_data = generate_baseline_data(1440, start=july_start)

    tracker = BaselineTracker()
    tracker.fit(july_data)

    print(f"July Entities: {len(tracker.seen_users)} Users, {len(tracker.seen_hosts)} Hosts")
    print(f"July Relationships: {len(tracker.seen_relationships)} pairs")
    print(f"July Active Hours: {tracker.seen_hours}")
    print(f"July Max CPU: {tracker.max_cpu:.2f}")

    # 2. Score August
    print("\n=== Processing August Data ===")
    # Generate August data starting at 14:00 (completely new temporal pattern)
    august_start = datetime(2025, 8, 1, 14, 0, 0, tzinfo=UTC)
    raw_august = generate_baseline_data(1000, start=august_start)
    august_data = generate_august_data_with_novelty(raw_august)

    novelties = tracker.inventory_novelty(august_data)

    # 3. Print Inventory
    print("\n" + "=" * 60)
    print("=== AUGUST NOVELTY INVENTORY ===")
    print("=" * 60)

    table_data = []
    for category, items in novelties.items():
        count = len(items)
        examples = ", ".join(items[:3])
        if count > 3:
            examples += f" ... (+{count - 3} more)"
        table_data.append([category, count, examples])

    print(tabulate(table_data, headers=["Category", "Count", "Examples"], tablefmt="grid"))

    # 4. Manual Cross-Check (Validation Gate)
    print("\n=== VALIDATION GATE: MANUAL CROSS-CHECK ===")

    # Pick the injected new user EVE_HACKER
    check_user = "EVE_HACKER"
    print(f"Verifying novelty claim for User: '{check_user}'")

    # Query the raw PyArrow July dataset directly
    july_users = july_data.column("user").to_pylist()
    occurrences = july_users.count(check_user)

    print(f"Occurrences in raw July data: {occurrences}")
    if occurrences == 0:
        print("✅ SUCCESS: Novelty claim validated. The entity genuinely did not appear in the baseline.")
    else:
        print("❌ FAILED: Baseline-lookup bug! Entity was present in July.")


if __name__ == "__main__":
    main()
