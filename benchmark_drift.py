"""
Diagnostic script to perform distribution-drift analysis between July and August.

Classifies features as:
1. Population Drift (Global dataset-wide statistical shift)
2. Operational Change (Plausible discrete new category mass)
3. Individual Anomaly (Global distribution unchanged, but extreme outliers exist)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pyarrow as pa
from scipy import stats
from tabulate import tabulate


def generate_july_baseline(n_windows: int, start: datetime) -> pa.Table:
    """Generate the July baseline data."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    event_counts = np.random.poisson(lam=10, size=n_windows)
    # Mean volume ~ 50
    f_volume = event_counts * np.random.normal(5, 0.5, n_windows)
    f_latency = np.random.normal(30, 2, n_windows)
    f_cpu = np.random.normal(30, 2, n_windows)

    users = ["alice", "bob", "service-account"]
    hosts = ["web-01", "db-01"]

    u_col = np.random.choice(users, size=n_windows, p=[0.4, 0.4, 0.2])
    h_col = np.random.choice(hosts, size=n_windows, p=[0.7, 0.3])

    return pa.table(
        {
            "window_start": timestamps,
            "event_count": event_counts.tolist(),
            "f_volume": f_volume.tolist(),
            "f_latency": f_latency.tolist(),
            "f_cpu": f_cpu.tolist(),
            "user": u_col.tolist(),
            "host": h_col.tolist(),
        }
    )


def generate_august_with_drift(n_windows: int, start: datetime) -> pa.Table:
    """Generate August data with specific injected drift behaviors."""
    timestamps = [start + timedelta(seconds=i * 5) for i in range(n_windows)]

    event_counts = np.random.poisson(lam=10, size=n_windows)

    # INJECTION 1: Population Drift on f_volume
    # Mean goes from 50 -> 60 (20% increase globally)
    f_volume = event_counts * np.random.normal(6.0, 0.5, n_windows)

    # Stable baseline for latency (No Drift)
    f_latency = np.random.normal(30, 2, n_windows)

    # INJECTION 2: Individual Anomaly on f_cpu
    # Distribution is mathematically identical to July, except for 5 extreme outliers.
    f_cpu = np.random.normal(30, 2, n_windows)
    for i in range(5):
        f_cpu[np.random.randint(0, n_windows)] = 999.0

    # INJECTION 3: Operational Change on host
    # 'new-web-02' comes online and takes 30% of traffic.
    users = ["alice", "bob", "service-account"]
    hosts = ["web-01", "db-01", "new-web-02"]

    u_col = np.random.choice(users, size=n_windows, p=[0.4, 0.4, 0.2])
    h_col = np.random.choice(hosts, size=n_windows, p=[0.5, 0.2, 0.3])

    return pa.table(
        {
            "window_start": timestamps,
            "event_count": event_counts.tolist(),
            "f_volume": f_volume.tolist(),
            "f_latency": f_latency.tolist(),
            "f_cpu": f_cpu.tolist(),
            "user": u_col.tolist(),
            "host": h_col.tolist(),
        }
    )


def analyze_continuous_drift(july: np.ndarray, august: np.ndarray, feature_name: str) -> tuple[str, str]:
    """Analyze continuous feature drift using Kolmogorov-Smirnov."""
    july_median = np.median(july)
    august_median = np.median(august)

    july_max = np.max(july)
    august_max = np.max(august)

    # Two-sample KS test
    ks_stat, p_value = stats.ks_2samp(july, august)

    median_shift_pct = abs(august_median - july_median) / max(july_median, 1e-6)

    if p_value < 0.01 and median_shift_pct >= 0.10:
        return "Population Drift", f"Median shifted by {median_shift_pct * 100:.1f}%. KS p-val < 0.01."

    if august_max > (july_max * 2):  # Very crude outlier check
        return (
            "Individual Anomaly (No Global Drift)",
            f"Global dist unchanged (KS p-val={p_value:.3f}), but contains extreme outliers (Aug Max: {august_max:.1f} vs Jul Max: {july_max:.1f}).",
        )

    return "No Drift", f"KS p-val={p_value:.3f}, Median Shift: {median_shift_pct * 100:.1f}%"


def analyze_categorical_drift(july: list[str], august: list[str], feature_name: str) -> tuple[str, str]:
    """Analyze categorical feature drift based on proportional shift."""
    july_counts = {k: july.count(k) for k in set(july)}
    august_counts = {k: august.count(k) for k in set(august)}

    n_aug = len(august)

    for category, count in august_counts.items():
        if category not in july_counts:
            prop = count / n_aug
            if prop >= 0.05:
                return "Operational Change", f"New category '{category}' represents {prop * 100:.1f}% of August mass."

    return "No Drift", "Categorical proportions stable."


def main() -> None:
    np.random.seed(42)

    print("=== Generating Datasets ===")
    july_data = generate_july_baseline(5000, datetime(2025, 7, 1, tzinfo=UTC))
    august_data = generate_august_with_drift(5000, datetime(2025, 8, 1, tzinfo=UTC))

    print("=== Analyzing Distribution Drift ===")

    results = []

    # Continuous Features
    for feature in ["f_volume", "f_latency", "f_cpu"]:
        j = july_data.column(feature).to_numpy()
        a = august_data.column(feature).to_numpy()
        classification, rationale = analyze_continuous_drift(j, a, feature)
        results.append([feature, "Continuous", classification, rationale])

    # Categorical Features
    for feature in ["user", "host"]:
        j = july_data.column(feature).to_pylist()
        a = august_data.column(feature).to_pylist()
        classification, rationale = analyze_categorical_drift(j, a, feature)
        results.append([feature, "Categorical", classification, rationale])

    print("\n" + "=" * 100)
    print("=== JULY -> AUGUST DRIFT REPORT ===")
    print("=" * 100)
    print(tabulate(results, headers=["Feature", "Type", "Classification", "Rationale"], tablefmt="grid"))


if __name__ == "__main__":
    main()
