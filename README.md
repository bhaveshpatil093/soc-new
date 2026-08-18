# TADS — Temporal Anomaly Detection System

## Research Question (Top-Level Success Criterion)

> **Can an unsupervised model, trained exclusively on July's cybersecurity
> telemetry to learn what "normal temporal behaviour" looks like, subsequently
> identify genuinely unusual patterns in completely unseen August data —
> including anomalies that existing monitoring infrastructure failed to surface?**

Every design decision, implementation choice, and experiment result in this
project is judged against this question. Success is NOT a polished 0–100 risk
score — it is whether the model surfaces **temporally novel behaviour** that
existing monitoring did not catch.

---

## Quick Start

```bash
# 1. Clone and enter the project
cd soc-new

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure credentials (Constraint #4: never hardcode)
cp .env.example .env
# Edit .env with your Elasticsearch credentials

# 5. Install pre-commit hooks
pre-commit install

# 6. Run tests
pytest
```

## Constraints

This project enforces 20 constraints. Key highlights:

| # | Constraint | Enforcement |
|---|-----------|-------------|
| 2 | ES READ-ONLY access | HTTP verb allowlist + tests |
| 4 | No credential leakage | Pre-commit hooks + log scrubber |
| 7 | 5-second temporal windows | Hardcoded constant + tests |
| 8 | Batch size is I/O only | Module separation + invariance tests |
| 12 | No batch-local normalization | Frozen training stats + tests |
| 16 | Parquet everywhere (no CSV) | Lint rules + pre-commit hooks |
| 17 | PyArrow/Polars/DuckDB over pandas | Lint rules |
| 20 | Full reproducibility | Seed management + checksum verification |

See `configs/base.yaml` for the complete constraint encoding.

## Architecture

```
Elasticsearch → Raw Parquet → 5-sec Windows → Features → Model → Results
     (READ)       (Stage 1)      (Stage 2)     (Stage 3)  (4/5)   (Stage 6)
```

- **July data** = training baseline (learn "normal")
- **August data** = completely unseen evaluation (detect "anomalous")
- **Normalization stats** frozen from July training set — never recomputed on August

## Project Structure

```
src/tads/           Main package
├── io/             Data ingestion (ES reader, Parquet writer, chunking)
├── windowing/      5-second temporal windowing
├── features/       Feature engineering + frozen normalization
├── models/         ML models (training, freezing, inference, scoring)
├── experiments/    Experiment config, runner, audit
├── analysis/       Anomaly ranking and reporting
└── utils/          Credentials, logging, hashing, memory
```

## License

MIT
