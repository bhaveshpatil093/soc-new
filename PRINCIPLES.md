# Engineering Principles

This document defines the core engineering principles for the Temporal Anomaly Detection System (TADS). Every principle here must be mechanically enforced wherever possible. 

## Core Principles

| Principle | Enforcement Mechanism | Status |
| :--- | :--- | :--- |
| **Reproducibility**<br>Identical inputs/config/seed produce identical outputs. | **Unit Tests:** `test_reproducibility` runs pipelines twice with the same seed and asserts identical SHA-256 output hashes. <br>**Runtime:** Global seeding applied at experiment start. | Enforced |
| **Deterministic Preprocessing**<br>No reliance on unordered sets or wall clock. | **Lint/Code Review:** Ban on `set()` for ordered data. <br>**Unit Tests:** Preprocessing pipelines tested for ordering invariance. | Mechanically Enforced + Code Review |
| **Configuration-Driven Behavior**<br>No magic numbers/thresholds in code. | **Unit Tests:** AST scans to detect hardcoded thresholds in `src/tads/models/` and `src/tads/features/`. <br>**Runtime:** Pydantic strict schema validation. | Enforced |
| **No Secrets in Source** | **Pre-commit Hook:** `detect-secrets` runs on every commit. <br>**Unit Tests:** AST scan for hardcoded credentials (`test_credentials.py`). | Enforced |
| **Strict Train/Test Separation**<br>July and August cannot structurally mix. | **Unit Tests:** `test_no_august_in_training` (Leakage test) inspects timestamps of all data passed to `.fit()` methods. <br>**Runtime:** Pipeline stage isolation. | Enforced |
| **Immutable Training Artifacts**<br>Artifacts are written once and never mutated. | **Unit Tests:** File system mock tests ensure `w` mode is used, not `a` or `r+`. <br>**Runtime:** Hashing artifacts upon creation; throwing errors if artifact exists. | Enforced |
| **Checkpointing & Resumability**<br>Long-running jobs persist resumable state without data loss/duplication. | **Integration Tests:** `test_pipeline_resume` interrupts a mock pipeline and restarts it, verifying final output matches uninterrupted run. | Enforced |
| **Scalable Data Processing**<br>No full-dataset in-memory materialization. | **Integration Tests:** Memory budget tests (`pytest-monitor` or `psutil` checks during test execution). <br>**Linting:** Ban on raw `pandas` imports. | Enforced |
| **Schema Versioning**<br>Canonical schema changes are versioned, migration is explicit. | **Unit Tests:** Parquet read/write tests assert schema version metadata. | Enforced |
| **Model Versioning**<br>Models tied to full lineage (data, config, commit). | **Runtime:** Artifact manifests explicitly record Git commit, config SHA, and input data SHA. | Enforced |
| **Structured Logging**<br>Machine-parseable JSON logs. | **Runtime:** `structlog` enforced across all modules. <br>**Unit Tests:** Log output validation. | Enforced |
| **Comprehensive Testing** | **CI Gate:** Coverage threshold (`fail_under = 80`). <br>**Code Review:** PRs require tests for new modules. | Enforced |

---

## Explicitly Prohibited Actions

The following actions are STRICTLY PROHIBITED.

| Prohibited Action | Enforcement Mechanism |
| :--- | :--- |
| **Training on August Data** | **Runtime / Unit Test:** Data validators explicitly check `max(timestamp)` < `2025-08-01` before allowing `.fit()`. |
| **Calculating August thresholds from August** | **Code Review / AST Scan:** `ThresholdCalculator` must only accept `training_stats`. |
| **Future events as causal features** | **Unit Test:** `test_temporal_causality` ensures feature vectors at time $T$ do not change when data at $T+1$ is modified. |
| **Current-batch min-max normalization** | **Unit Test:** `test_scorer_batch_independence` ensures an event scores identically alone vs. in a batch. |
| **Hardcoded attack rules / mal-IP lists** | **Code Review / AST Scan:** Banned string lists/regexes in model code. *Manual review required for logic checks.* |
| **Loading billions of records into RAM** | **Linting:** Pandas banned. **Testing:** Strict memory budget limits during integration tests. |
| **Silently dropping invalid records** | **Runtime:** Exception/logging framework requires explicit `DropReason` enum when dropping records. **Unit Test:** Asserts drop counts match expected invalid inputs. |

*Note on Manual Review:* While AST scanning can catch many hardcoded lists and pandas imports, detecting "stealth" signature-based rules (e.g., deeply nested `if dest_port == 4444: score=100`) requires human code review. We rely on architectural separation (models only see abstracted features, not raw IPs) to structurally prevent this.
