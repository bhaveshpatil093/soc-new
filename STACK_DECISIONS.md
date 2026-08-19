# TADS Technology Stack Decisions

The following technology stack has been selected for the Temporal Anomaly Detection System (TADS), optimized for scalability, out-of-core processing, and reproducibility against hundreds of millions to low billions of cybersecurity events.

| Technology | Purpose | Alternatives Considered | Decision Rationale | Scalability Note |
| :--- | :--- | :--- | :--- | :--- |
| **Python 3.11** | Core Language | Python 3.10, 3.12 | 3.11 provides massive performance gains over 3.10 and widespread ML library stability (unlike early 3.12 versions). | Provides the necessary C-extension compatibility for PyArrow/DuckDB. |
| **elasticsearch[async] 8.x** | ES/Kibana Client | HTTPX raw requests, elasticsearch 7.x | Official client handles connection pooling, retries, and scroll API natively. Version 8.x is chosen for modern Kibana/ES compatibility. | Scroll API allows streaming billions of rows without memory exhaustion. |
| **HTTPX** | Underlying HTTP Client | Requests, aiohttp | Replaces `Requests` in the ES client for robust async support and highly configurable connection pooling / timeout behavior. | Handles high concurrent throughput during ingestion. |
| **PyArrow (Parquet)** | Writer & Storage | fastparquet | PyArrow is the C++ Arrow implementation. Snappy compression provides the best balance of fast write/read throughput over file size. | Snappy decompression is extremely fast for sequential analytic scans. |
| **Apache Arrow** | In-Memory Format | Pandas (NumPy backend) | Arrow's columnar memory format enables zero-copy reads between Polars and DuckDB. *Failure Mode of Pandas:* Loading billions of rows into Pandas crashes with OOM errors. | Native chunking and zero-copy data passing. |
| **Polars (LazyFrame)** | Data Manipulation | Pandas, Dask | `LazyFrame` builds an optimized query plan before execution, pushing down filters to the Parquet reader. *Failure Mode of Dask:* Cluster overhead/complexity is overkill for a single high-memory node. | Processes datasets larger than RAM via streaming execution chunks. |
| **DuckDB** | Embedded SQL | SQLite, Pandas `.groupby()` | DuckDB executes vectorized SQL directly over Parquet/Arrow. Chosen for complex windowing logic where SQL is more expressive than dataframe APIs. | Out-of-core execution gracefully spills to disk instead of crashing on large aggregations. |
| **NumPy 2.x** | Dense Arrays | Native Python | Foundational for Scikit-Learn/PyTorch. | Essential for matrix math. |
| **Scikit-Learn** | Baseline Models (IForest) | PyOD | Scikit-Learn's Isolation Forest is robust and highly optimized. | Can be memory intensive during fitting, mitigated by downsampling/chunking. |
| **PyTorch** | Deep Learning Models | TensorFlow, JAX | PyTorch is the research standard. `torch.compile` provides massive speedups. | GPU acceleration natively supported. |
| **Pydantic + YAML** | Configuration | argparse, raw JSON | Pydantic enforces strict type and schema validation. *Failure Mode of raw dicts:* Silent failures when a config key is misspelled. | Fails fast on startup if config is invalid. |
| **Structlog (JSONL) + Parquet** | Experiment Tracking | MLflow, Weights & Biases | MLflow/W&B require external servers, violating the strict standalone/independent requirement. Structured JSONL logs + Parquet artifact dumps provide fully reproducible, grep-able runs. | Zero network overhead; infinitely scalable storage on disk. |
| **Pytest + pytest-cov** | Testing | unittest | Fixture support (PyArrow synthetic data) and parameterized testing are essential for the constraint matrices. | Negligible overhead. |
| **Structlog** | Logging | standard `logging` | Enforces JSON output with explicit context (run_id, stage, window_id) preventing string parsing nightmares. | Machine parseable at scale. |
| **Safetensors / Joblib** | Artifact Serialization | Pickle | `safetensors` for PyTorch (secure, zero-copy). `joblib` for sklearn. *Failure Mode of Pickle:* Arbitrary code execution vulnerabilities. | Fast loading of frozen models. |
| **PyTorch `MPS` / `CUDA`** | Optional GPU | CPU-only | PyTorch natively detects Apple Silicon (`mps`) or Nvidia (`cuda`), falling back to `cpu` automatically (`torch.device('cuda' if torch.cuda.is_available() else 'cpu')`). | Speeds up neural network training by 10x-100x. |
