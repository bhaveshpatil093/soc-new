# TADS — Temporal Anomaly Detection System

An unsupervised temporal anomaly detection system for cybersecurity telemetry.
TADS learns normal network and user behaviour from a baseline period (e.g. July) and detects anomalous activities in unseen data (e.g. August) without relying on signature-based alerts.

---

## 🛠️ 1. Environment Setup

Before running the pipeline on the office PC, ensure Python 3.11+ is installed.

### Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Linux/macOS
# OR on Windows:
# .venv\Scripts\activate
```

### Install Dependencies
Install the package in editable mode along with all required dependencies:
```bash
pip install -e .
pip install streamlit pyarrow pandas numpy torch elasticsearch
```

---

## 🔑 2. Elasticsearch / Kibana Configuration

The orchestrator explicitly refuses to run without connection details for the Elasticsearch cluster. You must configure these credentials via environment variables.

### Option A: Using `.env` file (Recommended)
Copy the example environment file:
```bash
cp .env.example .env
```
Edit `.env` and fill in your actual credentials:
```env
ELASTIC_HOST=https://your-office-elastic-cluster:9200
ELASTIC_USERNAME=elastic_user
ELASTIC_PASSWORD=super_secret_password
```
*Note: Make sure your `.env` file is loaded into your shell (e.g. using `export $(cat .env | xargs)` or letting a runner handle it). Alternatively, you can use Option B.*

### Option B: Exporting Variables Directly
Directly export the variables in your terminal before running the pipeline:
```bash
export ELASTIC_HOST="https://your-office-elastic-cluster:9200"
export ELASTIC_USERNAME="elastic_user"
export ELASTIC_PASSWORD="super_secret_password"

# Optional: If you want to change the target time ranges
export JULY_START="2025-07-01T00:00:00Z"
export JULY_END="2025-08-01T00:00:00Z"
export AUGUST_START="2025-08-01T00:00:00Z"
export AUGUST_END="2025-09-01T00:00:00Z"
```

---

## 🚀 3. Running the Pipeline End-to-End

The entire experiment is orchestrated by `run_pipeline.py`. It executes 13 individual stages automatically, gracefully catching failures and writing logs.

To start the pipeline:
```bash
python run_pipeline.py
```

### What happens when you run this?
1. **Connection Test:** Verifies the connection to Elasticsearch.
2. **July Ingestion:** Extracts logs from Elasticsearch for the July timeframe into Parquet files.
3. **July Profiling & Windowing:** Profiles data quality and groups events into 5-second semantic windows.
4. **Model Training:** Fits an ensemble of unsupervised ML models (Isolation Forest, PCA, LSTM, Autoencoder, Rarity, Statistical) on the July baseline.
5. **August Ingestion:** Extracts unseen August logs.
6. **August Profiling & Windowing:** Processes the August data into windows identical to July.
7. **August Inference:** Scores all August windows using the frozen July models.
8. **Reporting & Dashboard:** Generates a Top-100 anomaly report, synthesizes an experiment JSON bundle, and automatically launches the Streamlit Investigation Dashboard.

Logs for each stage are written to `pipeline_runs/<run_id>/<stage_name>.log`.

---

## 🔁 4. Resumability & Debugging

If the pipeline fails midway (e.g. due to a network timeout during August ingestion), you **do not** need to restart from the beginning. Every stage is strictly idempotent.

### Resuming from a specific stage
To resume, use the `--start-from` flag with the name of the stage where it failed.

For example, to resume from the August data extraction:
```bash
python run_pipeline.py --start-from ingest_august
```

### Running a single stage
To debug or run only a single specific stage:
```bash
python run_pipeline.py --only train_models
```

### Available Stages
* `test_connection`
* `ingest_july`
* `data_quality_july`
* `windows_july_index`
* `windows_july_build`
* `train_models`
* `ingest_august`
* `data_quality_august`
* `windows_august_index`
* `windows_august_build`
* `infer_august`
* `generate_reports`
* `dashboard`

---

## 📊 5. Analyzing Results (Dashboard)

At the end of a successful pipeline run, the script will automatically launch a Streamlit dashboard.

If you want to manually launch the dashboard at a later time (without rerunning the pipeline):
```bash
python run_pipeline.py --only dashboard
# or
streamlit run dashboard/app.py
```
Open your browser to `http://localhost:8501`. 

The dashboard provides read-only views of the anomaly timeline, the exact Top-100 candidates, the detector agreement profiles, feature deviations compared to the July baseline, and an analyst triage form.
