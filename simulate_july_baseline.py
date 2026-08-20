import numpy as np
import pyarrow as pa
from datetime import datetime, UTC, timedelta
from tads.baselines.statistics import RobustFeatureStatisticsBaseline
from tads.baselines.frequencies import HostFrequencyBaseline
import tempfile
from pathlib import Path

np.random.seed(42)

def generate_half_month(start_day: int, num_days: int) -> pa.Table:
    # 5-second windows for num_days
    total_windows = num_days * 24 * 60 * 12
    start_time = datetime(2025, 7, start_day, tzinfo=UTC)
    
    timestamps = [start_time + timedelta(seconds=i*5) for i in range(total_windows)]
    
    # Diurnal event count: higher during day, lower at night
    hours = np.array([t.hour for t in timestamps])
    is_day = (hours >= 8) & (hours <= 18)
    event_counts = np.where(is_day, np.random.poisson(50, total_windows), np.random.poisson(10, total_windows)).astype(float)
    
    # Introduce some missing values (5%)
    missing_mask = np.random.rand(total_windows) < 0.05
    
    # Introduce extreme outliers (e.g. 1 noisy host spikes)
    # Only in second half to see if it shifts? No, let's put it in both halves but randomly
    spike_mask = np.random.rand(total_windows) < 0.001
    event_counts[spike_mask] = np.random.uniform(5000, 20000, np.sum(spike_mask))
    
    # Convert missing to None
    event_counts_list = [None if m else v for m, v in zip(missing_mask, event_counts)]
    
    return pa.table({
        "window_start": timestamps,
        "event_count": event_counts_list,
        "host_name": ["normal_host"] * total_windows  # Simplified for this test
    })

def main():
    print("Generating H1 data...")
    h1 = generate_half_month(1, 15)
    print("Generating H2 data...")
    h2 = generate_half_month(16, 15)
    
    # Inject an extreme noisy host into H2 to test sensitivity
    # Let's say window 0 of H2 gets a crazy host
    h2_hosts = h2.column("host_name").to_pylist()
    h2_hosts[100] = "crazy_noisy_host"
    h2 = h2.set_column(2, "host_name", pa.array(h2_hosts))
    
    h1_stats = RobustFeatureStatisticsBaseline(features=["event_count"])
    h1_stats.fit(h1)
    
    h2_stats = RobustFeatureStatisticsBaseline(features=["event_count"])
    h2_stats.fit(h2)
    
    h1_freq = HostFrequencyBaseline()
    h1_freq.fit(h1)
    
    h2_freq = HostFrequencyBaseline()
    h2_freq.fit(h2)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        h1_stats.save(tmp_path, "h1")
        h2_stats.save(tmp_path, "h2")
        
        h1_load = RobustFeatureStatisticsBaseline(features=["event_count"])
        h1_load.load(tmp_path, "h1")
        s1 = h1_load.get_statistics("event_count")
        
        h2_load = RobustFeatureStatisticsBaseline(features=["event_count"])
        h2_load.load(tmp_path, "h2")
        s2 = h2_load.get_statistics("event_count")
        
        print(f"H1 Stats: {s1}")
        print(f"H2 Stats: {s2}")
        
        print(f"H1 Freq: {h1_freq.get_frequency('normal_host')}")
        print(f"H2 Freq: {h2_freq.get_frequency('normal_host')}, {h2_freq.get_frequency('crazy_noisy_host')}")

if __name__ == "__main__":
    main()
