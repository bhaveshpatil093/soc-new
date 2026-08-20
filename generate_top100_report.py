"""
Generate the Top-100 August Anomaly Report in JSON, Parquet, and Markdown formats.
"""

import json
import torch
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import UTC, datetime
from pathlib import Path

from rank_august_windows import generate_realistic_features, inject_anomalies
from tads.inference.pipeline import AugustInferencePipeline
from tads.models.detectors.ensemble import EnsembleDetector
from tads.models.detectors.isolation_forest import IsolationForestDetector
from tads.models.detectors.pca import PCADetector
from tads.models.detectors.rarity import RarityDetector
from tads.models.detectors.statistical import RobustStatisticalDetector
from tads.models.detectors.autoencoder import AutoencoderDetector
from tads.models.detectors.sequence_lstm import SequenceLSTMDetector

def main() -> None:
    # 1. Deterministic Seeding
    np.random.seed(42)
    torch.manual_seed(42)
    
    # 2. Setup Baseline & Pipeline
    cont_features = ["f_volume", "f_latency", "f_cpu", "f_mem"]
    cat_features = ["user", "host"]
    
    july_start = datetime(2025, 7, 1, tzinfo=UTC)
    july_data = generate_realistic_features(10000, start=july_start)
    
    july_medians = {
        "event_count": np.median(july_data.column("event_count").to_numpy()),
        "f_volume": np.median(july_data.column("f_volume").to_numpy()),
        "f_latency": np.median(july_data.column("f_latency").to_numpy()),
        "f_cpu": np.median(july_data.column("f_cpu").to_numpy()),
        "f_mem": np.median(july_data.column("f_mem").to_numpy()),
    }
    
    detectors = {
        "IForest": IsolationForestDetector(feature_columns=cont_features, n_jobs=1),
        "PCA": PCADetector(feature_columns=cont_features, target_explained_variance=0.95),
        "Statistical": RobustStatisticalDetector(feature_columns=cont_features),
        "Rarity": RarityDetector(feature_columns=cat_features),
        "Autoencoder": AutoencoderDetector(
            feature_columns=cont_features, hidden_dim=8, latent_dim=3, epochs=1, batch_size=256
        ),
        "LSTM": SequenceLSTMDetector(
            feature_columns=cont_features, seq_len=10, hidden_dim=16, num_layers=1, epochs=1, batch_size=128
        ),
    }
    
    ensemble = EnsembleDetector(detectors=detectors, strategy="max")
    ensemble.fit(july_data)
    
    august_start = datetime(2025, 8, 1, tzinfo=UTC)
    raw_august = generate_realistic_features(5000, start=august_start)
    august_data = inject_anomalies(raw_august)
    
    pipeline = AugustInferencePipeline(detectors=detectors, ensemble_strategy="max")
    results = pipeline.score_all(august_data)
    
    # 3. Extract Top 100
    ens_ev = results.column("ensemble_evidence").to_numpy()
    sum_ev = np.sum([results.column(f"evidence_{n}").to_numpy() for n in detectors.keys()], axis=0)
    
    # Filter for anomalies crossing 0.90
    threshold = 0.90
    valid_indices = np.where(ens_ev >= threshold)[0]
    
    # Sort valid indices
    valid_ens_ev = ens_ev[valid_indices]
    valid_sum_ev = sum_ev[valid_indices]
    
    # Sort by ens_ev, then sum_ev
    sorted_local = np.lexsort((valid_sum_ev, valid_ens_ev))[::-1]
    top_indices = valid_indices[sorted_local][:100]
    
    explanations = ensemble.explain(august_data).to_pylist()
    
    report_data = []
    
    for rank, idx in enumerate(top_indices, 1):
        window_start = august_data.column("window_start")[idx].as_py()
        evidence = ens_ev[idx]
        category = results.column("primary_category")[idx].as_py()
        
        # Detector Agreement
        agreed_detectors = []
        for name in detectors.keys():
            if results.column(f"evidence_{name}")[idx].as_py() >= 0.90:
                agreed_detectors.append(name)
        
        # July Comparison
        july_comp = {}
        for f in ["event_count", "f_volume", "f_latency", "f_cpu", "f_mem"]:
            val = august_data.column(f)[idx].as_py()
            baseline = july_medians[f]
            ratio = val / baseline if baseline > 0 else 0
            july_comp[f] = {"val": float(val), "median": float(baseline), "ratio": float(ratio)}
            
        # Novel Relationships
        novel_relationships = []
        if "Rarity" in agreed_detectors:
            novel_relationships.append(f"User: {august_data.column('user')[idx].as_py()} | Host: {august_data.column('host')[idx].as_py()}")
            
        # Model-only status
        # Simulate: True if it's a behavioural or statistical anomaly caught only by ML
        model_only = category in ["behavioural_anomaly", "statistical_anomaly"]
        
        row = {
            "rank": rank,
            "timestamp": window_start.isoformat() if isinstance(window_start, datetime) else str(window_start),
            "duration": "5s",
            "ensemble_evidence": float(evidence),
            "category": category,
            "detector_agreement": agreed_detectors,
            "top_anomalous_features": str(explanations[idx]),
            "july_comparison": july_comp,
            "novel_relationships": novel_relationships,
            "affected_entities": {
                "user": august_data.column("user")[idx].as_py(),
                "host": august_data.column("host")[idx].as_py(),
            },
            "related_events": int(august_data.column("event_count")[idx].as_py()),
            "model_only_status": model_only,
            "analyst_status": "Pending"
        }
        report_data.append(row)
        
    # Export JSON
    output_dir = Path("artifacts")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    with open(output_dir / "top100_report.json", "w") as f:
        json.dump(report_data, f, indent=2)
        
    # Export Parquet
    # Flatten dicts/lists for parquet compatibility where necessary, or use pyarrow's struct types
    # Simple trick: serialize dicts/lists to JSON strings for robust columnar storage
    pq_data = []
    for row in report_data:
        flat_row = row.copy()
        flat_row["detector_agreement"] = json.dumps(row["detector_agreement"])
        flat_row["july_comparison"] = json.dumps(row["july_comparison"])
        flat_row["novel_relationships"] = json.dumps(row["novel_relationships"])
        flat_row["affected_entities"] = json.dumps(row["affected_entities"])
        pq_data.append(flat_row)
        
    pq_table = pa.Table.from_pylist(pq_data)
    pq.write_table(pq_table, output_dir / "top100_report.parquet")
    
    # Export Markdown
    with open(output_dir / "top100_report.md", "w") as f:
        f.write("# Top-100 August Anomalies Report\n\n")
        f.write(f"*Generated on {datetime.now(UTC).isoformat()}*\n\n")
        
        for row in report_data:
            f.write(f"## [{row['rank']}] Timestamp: {row['timestamp']}\n")
            f.write(f"- **Ensemble Evidence:** {row['ensemble_evidence']:.4f}\n")
            f.write(f"- **Category:** {row.get('category', 'Unknown')}\n")
            f.write(f"- **Duration:** {row['duration']}\n")
            f.write(f"- **Affected Entities:** User: `{row['affected_entities']['user']}`, Host: `{row['affected_entities']['host']}`\n")
            f.write(f"- **Related Events:** {row['related_events']} events\n")
            f.write(f"- **Model-Only Candidate:** {row['model_only_status']}\n")
            f.write(f"- **Analyst Status:** {row['analyst_status']}\n\n")
            
            f.write("### Detection Profile\n")
            f.write(f"- **Detectors Agreed:** {', '.join(row['detector_agreement'])}\n")
            f.write(f"- **Top Features:** {row['top_anomalous_features']}\n\n")
            
            if row['novel_relationships']:
                f.write("### Novel Relationships\n")
                for nr in row['novel_relationships']:
                    f.write(f"- {nr}\n")
                f.write("\n")
                
            f.write("### July Baseline Comparison\n")
            f.write("| Feature | Value | July Median | Ratio |\n")
            f.write("|---------|-------|-------------|-------|\n")
            for feat, comp in row['july_comparison'].items():
                f.write(f"| {feat} | {comp['val']:.2f} | {comp['median']:.2f} | {comp['ratio']:.2f}x |\n")
            f.write("\n---\n\n")

    print(f"Generated Top-100 report with {len(report_data)} qualifying candidates.")
    
if __name__ == "__main__":
    main()
