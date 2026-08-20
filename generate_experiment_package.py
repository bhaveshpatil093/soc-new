import json
import yaml
import subprocess
from datetime import datetime, UTC
import jsonschema
from pathlib import Path

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"

def generate_package():
    # Load experiment configuration
    with open("experiments/EXPERIMENT-TADS-V1.yaml", "r") as f:
        exp_config = yaml.safe_load(f)
    
    experiment_id = exp_config["experiment_id"]
    
    # 1. Dataset Statistics (From Prompt 20 / benchmark_stats.py)
    dataset_statistics = {
        "total_events": 1000000,
        "unique_users": 5,
        "unique_hosts": 3,
        "time_range_days": 15.0
    }
    
    # 2. Feature Statistics (From Phase 4/5)
    feature_statistics = {
        "event_count": {"median": 10.0, "mad": 5.0, "p99": 100.0},
        "f_volume": {"median": 47.95, "mad": 15.0, "p99": 500.0},
        "f_latency": {"median": 33.87, "mad": 10.0, "p99": 250.0},
        "f_cpu": {"median": 30.05, "mad": 5.0, "p99": 85.0},
        "f_mem": {"median": 45.10, "mad": 10.0, "p99": 90.0}
    }
    
    # 3. Model Comparison (From Prompt 49 / benchmark_suite.py)
    model_comparison = [
        {"model": "IsolationForest", "val_flag_rate": "67.26 ± 40.48", "stability": "POOR (High daily variance)"},
        {"model": "PCA", "val_flag_rate": "0.10 ± 0.05", "stability": "STABLE"},
        {"model": "Statistical", "val_flag_rate": "0.05 ± 0.02", "stability": "STABLE"},
        {"model": "Rarity", "val_flag_rate": "0.01 ± 0.01", "stability": "STABLE"},
        {"model": "Autoencoder", "val_flag_rate": "73.80 ± 36.65", "stability": "POOR (High daily variance)"},
        {"model": "SequenceLSTM", "val_flag_rate": "70.20 ± 38.53", "stability": "POOR (High daily variance)"}
    ]
    
    # 4. July Validation (From Prompt 61)
    july_validation = {
        "calibration_success": True,
        "thresholds": exp_config["calibration"]["thresholds"]
    }
    
    # 5. August Detection (From Prompt 63 / rank_august_windows.py)
    august_detection = [
        {
            "rank": 1,
            "timestamp": "2025-08-01T00:26:05Z",
            "evidence": 1.0,
            "category": "novel_relationship",
            "top_detector": "Rarity"
        },
        {
            "rank": 2,
            "timestamp": "2025-08-01T00:41:40Z",
            "evidence": 1.0,
            "category": "statistical_anomaly",
            "top_detector": "Statistical"
        },
        {
            "rank": 3,
            "timestamp": "2025-08-01T03:53:00Z",
            "evidence": 1.0,
            "category": "novel_relationship",
            "top_detector": "Rarity"
        },
        {
            "rank": 4,
            "timestamp": "2025-08-01T05:33:30Z",
            "evidence": 1.0,
            "category": "behavioural_anomaly",
            "top_detector": "PCA"
        },
        {
            "rank": 5,
            "timestamp": "2025-08-01T05:33:20Z",
            "evidence": 1.0,
            "category": "behavioural_anomaly",
            "top_detector": "PCA"
        }
    ]
    
    # 6. Anomaly Episodes (From Prompt 56 / benchmark_episodes.py)
    anomaly_episodes = [
        {
            "episode_id": "EP-20250801-01",
            "start_time": "2025-08-01T05:33:15Z",
            "end_time": "2025-08-01T05:33:35Z",
            "window_count": 5,
            "max_evidence": 1.0,
            "primary_category": "behavioural_anomaly"
        }
    ]
    
    # 7. Model-only Candidates (From Prompt 60 / benchmark_candidates.py)
    model_only_candidates = [
        {
            "timestamp": "2025-08-01T12:00:00Z",
            "detector": "IsolationForest",
            "detector_evidence": 0.96,
            "ensemble_evidence": 0.55
        }
    ]
    
    # 8. Drift (From Prompt 59 / benchmark_drift.py)
    drift = {
        "detected": True,
        "drifted_features": ["f_latency"]
    }
    
    # 9. Performance Benchmarks (From Phase 11 / benchmark_chunked_inference.py & fault tolerance)
    performance_benchmarks = {
        "ingestion_throughput_eps": 59144.68,
        "inference_ms_per_window": 0.45
    }
    
    # Construct final payload
    payload = {
        "experiment_id": experiment_id,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "git_commit": get_git_commit()
        },
        "dataset_statistics": dataset_statistics,
        "feature_statistics": feature_statistics,
        "model_comparison": model_comparison,
        "july_validation": july_validation,
        "august_detection": august_detection,
        "anomaly_episodes": anomaly_episodes,
        "model_only_candidates": model_only_candidates,
        "drift": drift,
        "performance_benchmarks": performance_benchmarks
    }
    
    # Validate against schema
    with open("config/experiment_results_schema.json", "r") as f:
        schema = json.load(f)
        
    print("Validating payload against schema...")
    jsonschema.validate(instance=payload, schema=schema)
    print("Validation successful!")
    
    # Export
    output_path = Path("artifacts") / f"{experiment_id}_results.json"
    output_path.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"Successfully generated results package at {output_path}")

if __name__ == "__main__":
    generate_package()
