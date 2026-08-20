# Unsupervised Temporal Anomaly Detection — Detailed 75-Prompt Build Sequence

This is the original 75-prompt / 12-phase sequence, expanded so each prompt carries
enough detail that a coding agent cannot skip understanding, benchmarking, testing,
or validating a stage before moving to the next one. **Nothing about the original
architecture, order, constraints, or phase boundaries has been changed** — every
constraint, prohibition, and requirement from the source document is preserved
verbatim in spirit; each prompt has simply been expanded with explicit deliverables,
required benchmarks/tests, and a validation gate the agent must pass before
proceeding.

Architecture reference (unchanged):

```text
Kibana/Elasticsearch → streaming extraction → Parquet → PyArrow/Polars/DuckDB
→ 5-second windows → feature store → July training → frozen models
→ August inference → anomaly episodes → investigation results
```

---

# PHASE 0 — PROJECT FOUNDATION

## Prompt 1 — Start completely from scratch

```text
We are building a completely NEW and INDEPENDENT cybersecurity anomaly detection
research system.

Do NOT modify, reuse, import, copy, or depend on the existing SOC project. Do not
add the new project as a submodule, symlink, or shared package of the old one.
Confirm this by showing that the new repository has zero import paths, zero
config references, and zero file-system references into the old project's
directory tree.

OBJECTIVE
Build an unsupervised temporal anomaly detection system capable of learning
normal cybersecurity behaviour from JULY data and detecting previously unseen
anomalous behaviour in AUGUST data.

The most important research objective is NOT creating a fancy 0-100 risk score.
The important objective is:

"Can a model trained only on July identify unusual temporal behaviour in unseen
August data, including potentially important anomalies that existing monitoring
did not surface?"

Restate this research question back to me in your own words before proceeding,
and keep it visible in the project README as the top-level success criterion
against which every later phase will be judged.

CONSTRAINTS (all must be explicitly acknowledged and encoded as project rules,
not just prose):

1. Data source is Kibana/Elasticsearch.
2. Access is READ ONLY — no write, update, delete, index-management, or
   ILM-mutating API calls anywhere in the codebase.
3. I have host, username and password credentials.
4. Credentials must NEVER be hardcoded, logged, committed, or embedded in any
   artifact (model file, config snapshot, manifest, error message).
5. July is training/baseline data.
6. August is completely unseen evaluation data.
7. Primary temporal unit is a 5-second window.
8. Do NOT use arbitrary batches such as 10,000 logs as the semantic unit —
   batch size is purely an I/O/performance concern and must never leak into
   feature semantics, window boundaries, or evaluation logic.
9. Internal chunking for efficient I/O is allowed and expected, but must be
   clearly separated in code/module structure from the temporal windowing
   layer.
10. No static cybersecurity detection rules as the core detector.
11. Do not reproduce Elastic/Kibana rules.
12. Do not use current-batch min-max normalization for anomaly scores (this
    would make an event's "anomalousness" depend on what else happens to be
    in the same processing batch, which is not scientifically valid).
13. The system must support very large datasets (design for hundreds of
    millions to low billions of events without loading them into RAM at once).
14. Compute availability is not the limiting factor during final experiments.
15. Storage and memory efficiency still matter — do not treat #14 as license
    for wasteful design.
16. Use Parquet rather than CSV, everywhere, including intermediate artifacts.
17. Prefer PyArrow/Polars/DuckDB and other scalable, columnar, out-of-core
    processing tools over pandas-in-memory patterns.
18. UI is secondary — no dashboard work before Phase 12.
19. Backend correctness, scientific validity, scalability, and detection
    quality are the priorities, in that order when trade-offs arise.
20. Every training artifact must be reproducible: same inputs + same config +
    same seed = same outputs, byte-for-byte or within documented numerical
    tolerance.

DELIVERABLE — before writing any implementation code, produce a design document
covering:
- system architecture (component diagram)
- directory structure
- technology choices with justification
- data flow (Kibana → Parquet → windows → features → models → results)
- ML methodology (train/validate/freeze/infer lifecycle)
- experiment methodology (how an experiment is defined, run, and audited)
- major risks and how each will be mitigated or monitored
- testing strategy (unit, integration, data-quality, leakage-detection tests)

VALIDATION GATE: Do not write any implementation code until this design
document is reviewed and I explicitly approve moving to Prompt 2. Flag any
constraint above that you believe conflicts with another constraint, rather
than silently resolving the conflict yourself.
```

---

## Prompt 2 — Establish engineering principles

```text
Define the engineering principles for this new repository, and encode them
both as a written PRINCIPLES.md and, wherever mechanically possible, as
enforced checks (lint rules, pre-commit hooks, CI gates, or runtime
assertions) rather than only as prose that can be silently violated later.

The system must follow:

- reproducibility — identical inputs/config/seed produce identical outputs
- deterministic preprocessing — no reliance on unordered set iteration, wall
  clock, or non-fixed random state anywhere in the data path
- configuration-driven behavior — no magic numbers/thresholds embedded in
  code; everything tunable lives in versioned config files
- no secrets in source — enforce with a secret-scanning pre-commit hook
- strict train/test separation — July and August must be structurally
  incapable of mixing (see below)
- immutable training artifacts — once frozen, a model/baseline/threshold
  artifact is written once and never mutated in place; changes produce a
  new versioned artifact
- checkpointing — long-running jobs persist resumable state
- resumability — a killed job can be restarted without data loss or
  duplication
- scalable data processing — no full-dataset in-memory materialization
- schema versioning — canonical schema changes are versioned and migration
  is explicit
- model versioning — every trained model has an immutable version id tied
  to its full lineage (data, features, config, code commit)
- structured logging — machine-parseable logs (e.g. JSON lines) with
  consistent fields (run_id, stage, level, message, timestamp)
- comprehensive testing — unit tests per module, integration tests per
  pipeline stage, and dedicated leakage/isolation tests

EXPLICITLY PROHIBITED (write these as things CI or code review must catch,
not just as reminders):

- training on August
- calculating August thresholds from August
- using future events to construct causal features
- current-batch min-max anomaly normalization
- hardcoded attack rules
- hardcoded malicious IP/process lists as anomaly decisions
- loading billions of records into RAM
- silently dropping invalid records (every dropped/rejected record must be
  counted and logged with a reason code)

DELIVERABLE: PRINCIPLES.md plus a short "How this is enforced" table mapping
each principle to a concrete mechanism (test name, CI check, lint rule,
runtime assertion). Where a principle cannot be mechanically enforced, say so
explicitly and propose a manual review checkpoint instead.

VALIDATION GATE: Show at least one working example of an enforcement
mechanism (e.g. a test that fails if an August timestamp appears in a
July-only fitting function) before moving to Prompt 3.
```

---

## Prompt 3 — Choose the technology stack

```text
Select the technology stack for the standalone project. Evaluate and choose
appropriate technologies for:

- Python (version, packaging approach)
- Elasticsearch/Kibana access (client library, version compatibility)
- HTTP client (timeout/retry behavior, connection pooling)
- Parquet (writer library, compression codec)
- Arrow (in-memory representation strategy)
- Polars (lazy vs eager evaluation strategy)
- DuckDB (embedded analytical queries over Parquet)
- NumPy
- scikit-learn
- PyTorch
- configuration (schema-validated config format, e.g. pydantic + YAML)
- experiment tracking (how runs, params, and metrics are recorded)
- testing (framework, coverage tooling)
- logging (structured logging library)
- serialization (model/artifact format choices)
- optional GPU processing (how it's detected, and how the system degrades
  gracefully without one)

Do not select libraries simply because they are popular.

For every major technology explain:
- why it is needed
- scalability implications at the target data volume (hundreds of millions
  to low billions of events)
- alternatives seriously considered
- why the chosen option is preferred, with a concrete failure mode of the
  rejected alternative

DELIVERABLE: a stack decision table (technology | purpose | alternatives
considered | decision rationale | scalability note) plus a minimal
`pyproject.toml`/dependency lockfile reflecting the chosen versions.

VALIDATION GATE: Before finalizing, run a tiny synthetic benchmark (a few
hundred thousand synthetic rows) proving the chosen Parquet + Polars/DuckDB
combination can read, filter, and aggregate without loading the full dataset
into a single in-memory pandas DataFrame. Show the benchmark output.
```

---

## Prompt 4 — Create the repository

```text
Create the complete standalone repository structure.

Use a clean architecture such as:

src/
tests/
configs/
scripts/
data/
artifacts/
experiments/
docs/

Design modules for:

ingestion       — Kibana/Elasticsearch read access, streaming extraction
storage         — Parquet read/write, partitioning, manifests
schema          — canonical schema definitions and versioning
validation      — data-quality checks, invalid-record handling
windowing       — 5-second window assignment and temporal indexing
features        — modular feature computation (per feature group)
baselines       — July-only statistical/frequency baselines
models          — detector implementations (Isolation Forest, autoencoder,
                   sequence model, statistical, PCA, rarity)
calibration     — converting raw model scores into comparable evidence
inference       — frozen-artifact August inference pipeline
explanation     — event/feature attribution for anomalous windows
evaluation      — benchmarking, drift analysis, candidate validation
experiments     — experiment definition, freezing, and manifesting

Do not put everything into one Python file. Each module above should be an
importable package with its own `__init__.py`, its own tests directory
mirror under `tests/`, and a short module-level docstring stating its single
responsibility and what it explicitly does NOT do.

Do not build Streamlit yet.

DELIVERABLE: initial package structure, pyproject configuration, dependency
management, linting (e.g. ruff/black) and testing (pytest) setup, plus a
`make check` (or equivalent) command that runs lint + type-check + tests in
one step.

VALIDATION GATE: Run the empty test suite and lint/type-check successfully
(even with placeholder modules) to prove the scaffolding is wired correctly
before any real logic is added.
```

---

## Prompt 5 — Environment and secrets

```text
Implement secure environment configuration.

Required environment variables:

ELASTIC_HOST
ELASTIC_USERNAME
ELASTIC_PASSWORD

Potentially support:

ELASTIC_CA_CERT
ELASTIC_VERIFY_TLS
ELASTIC_TIMEOUT

Never write credentials into:
- Python files
- YAML
- JSON
- logs
- Git
- model artifacts

Implementation requirements:
- Load config via a single, centralized settings module (e.g. pydantic
  Settings) so there is exactly one place that reads environment variables.
- Create `.env.example` containing placeholders only, with comments
  explaining each variable and its default/expected format.
- Add configuration validation that runs at process start: check presence,
  basic format (e.g. host is a URL, timeout is a positive number).
- If credentials are missing or malformed, fail fast with a clear,
  actionable error message that does NOT echo back the invalid value if it
  could contain a partial secret.
- Never print passwords or authentication headers — write a unit test that
  asserts no log line, exception message, or repr() output ever contains the
  literal password value, by injecting a known dummy secret and grepping
  captured output.

VALIDATION GATE: Demonstrate three failure paths (missing var, malformed
host, unreachable host) and show the resulting error messages, confirming
none of them leak the secret value.
```

---

# PHASE 1 — ELASTIC/KIBANA INGESTION

## Prompt 6 — Read-only connection architecture

```text
Implement a read-only Elasticsearch/Kibana data-source abstraction.

The client must expose:

connect()
validate_connection()
discover_sources()
discover_fields()
count_events()
stream_events()

Requirements:
- The implementation must never call write APIs — enforce this by using a
  restricted wrapper around the underlying client that only exposes the
  read-oriented methods above, rather than trusting callers not to reach
  for `.index()`/`.delete()`/`.update()` on the raw client.
- Support TLS, authentication, timeout and retries (with exponential
  backoff and a bounded max-retry count, both configurable).
- Do not assume a specific index name — index/data-stream selection must be
  configurable, with no default that silently targets production indices.
- Add a unit test using a mocked/faked Elasticsearch client that asserts
  none of the write-capable methods exist on the abstraction's public
  interface.

VALIDATION GATE: Show the abstraction's public API surface (e.g. via
`dir()` or a generated interface doc) and confirm it contains only the six
read methods listed above plus any additional read-only helpers explicitly
approved.
```

---

## Prompt 7 — Connection diagnostics

```text
Create a CLI diagnostic:

python -m anomaly_system ingest test-connection

It must report:

connection status
authentication status
authorization status
available data sources
timestamp fields
sample event availability

Requirements:
- Never expose credentials in the CLI output, including in verbose/debug
  mode.
- Provide clear, distinct diagnostics for each of the following failure
  categories, with a specific human-readable message and remediation hint
  for each:
  401 (authentication failed — check username/password)
  403 (authorization failed — account lacks required index privileges)
  404 (target index/data stream not found — check configuration)
  timeout (connection or read timeout — check network/latency)
  TLS failure (certificate validation failed — check CA cert/verify flag)
  DNS failure (host could not be resolved)
  connection refused (host reachable but port/service not accepting
  connections)
- Exit codes must differ meaningfully by failure category so the command
  is scriptable.

VALIDATION GATE: Demonstrate the diagnostic command against at least three
simulated failure conditions (e.g. wrong password, wrong host, blocked
port) and one success condition, showing distinct, correct messages for
each.
```

---

## Prompt 8 — Source discovery

```text
Implement automatic discovery of available Elasticsearch indices/data
streams.

For each source determine:

name
type
field availability
timestamp field candidates
earliest timestamp if discoverable
latest timestamp if discoverable
approximate document count if safely available

Requirements:
- Do not download the dataset — discovery must use metadata/mapping and
  aggregation queries only, never a full document scan.
- Allow explicit source configuration to override discovery entirely (for
  cases where auto-discovery picks the wrong index or the account lacks
  list-indices privileges).
- Cap and document the cost of any discovery query (e.g. count queries
  should use `track_total_hits` sensibly, not scroll the whole index).
- Handle indices with no discoverable timestamp field gracefully (report
  as "no timestamp candidate found" rather than crashing).

VALIDATION GATE: Run discovery against the real (or a representative test)
cluster and show the structured output for at least one real index,
including a case where a field is missing/unmapped and the code handles it
without raising.
```

---

## Prompt 9 — Schema discovery

```text
Implement source schema inspection.

Discover the actual fields present in the logs.

Identify security-relevant fields such as:

@timestamp
event.*
user.*
source.*
destination.*
host.*
process.*
network.*
file.*
agent.*
log.*

Requirements:
- Do not assume ECS compliance — treat ECS field names as candidates to
  look for, not guarantees.
- Create a mapping layer from source fields to canonical internal fields,
  implemented as an explicit, inspectable mapping table/config (not
  string-matching logic scattered through the codebase).
- Preserve unknown fields — fields that don't map to any canonical field
  must still be retained (e.g. in a side `raw`/`extra` column or
  passthrough store), not silently dropped.
- Log a summary of mapping coverage: how many discovered fields mapped
  successfully vs. how many are unmapped/unknown.

VALIDATION GATE: Produce a mapping coverage report against the real schema
showing percentage of security-relevant canonical fields that were
successfully located, and list any expected fields that could not be
found.
```

---

## Prompt 10 — Streaming extraction

```text
Implement scalable event extraction.

Requirements:

- time-range filtering (inclusive/exclusive boundary semantics must be
  explicit and tested)
- search_after or PIT (point-in-time) where appropriate, chosen based on
  cluster version/capability and documented
- configurable page size
- bounded memory — peak memory must not scale with total result-set size,
  only with page size
- retries with backoff on transient failures
- checkpointing (see Prompt 11)
- resumability
- deterministic ordering as far as the source permits (e.g. sort by
  timestamp then a stable tiebreaker field/id)
- graceful interruption (SIGINT/SIGTERM triggers a clean checkpoint and
  exit rather than a partial, uncheckpointed state)

Expose:

stream_events(start, end)

The generator must yield manageable chunks. Never build a Python list
containing the entire month.

VALIDATION GATE: Extract a bounded multi-day sample and demonstrate (a)
peak memory stays roughly flat as the time range grows (measure and report
memory at small vs. larger ranges), and (b) killing the process mid-run and
restarting resumes without re-fetching already-checkpointed data or
producing duplicates.
```

---

## Prompt 11 — Extraction checkpoints

```text
Implement extraction checkpointing.

The checkpoint must record:

source
time range
last successfully processed cursor/search_after state
partition
event count
timestamp
software version

Requirements:
- Checkpoints must be written atomically (write to temp file + rename, or
  equivalent) so a crash mid-write never leaves a corrupt/partial
  checkpoint.
- The extraction must resume from the checkpoint after failure, continuing
  exactly from the last acknowledged cursor.
- Ensure retries cannot silently duplicate output: define and test the
  exactly-once (or explicitly documented at-least-once + dedup) semantics
  across a checkpoint boundary.
- Store checkpoints per extraction run (July run and August run must have
  independent checkpoint files/namespaces).

VALIDATION GATE: Simulate a crash immediately after a checkpoint write and
immediately before one; show that both cases resume correctly and that the
resulting Parquet output contains no duplicate event IDs across the full
run (verify with a dedup count test, not just visual inspection).
```

---

## Prompt 12 — Raw Parquet writer

```text
Implement the canonical raw storage layer.

Do NOT use CSV. Use Parquet with Arrow-compatible schemas.

Partition by date and optionally hour.

Requirements:

- compression (choose and justify a codec, e.g. zstd, balancing ratio vs.
  read speed)
- configurable row groups (document the chosen default and why)
- append-safe writes (concurrent or sequential appends must not corrupt
  existing partitions)
- schema consistency (writer must reject or explicitly coerce records that
  don't match the canonical Arrow schema, never silently write a mismatched
  schema into the same partition)
- bounded memory (writer streams row groups rather than buffering an
  entire partition in memory)
- atomic partition completion (a partition directory is only considered
  "complete" once a completion marker/manifest entry is written, so a
  reader never sees a half-written partition as done)
- manifest generation (see Prompt 13)

The raw Parquet data should preserve source events as faithfully as
practical. Do not perform destructive feature engineering at this stage —
this layer is a faithful, queryable copy of the source, not a derived
dataset.

VALIDATION GATE: Write a multi-partition sample, then verify with an
independent read (e.g. via DuckDB) that (a) row counts match the source
count reported during extraction, (b) schema is uniform across partitions,
and (c) a simulated interrupted write does not leave a partition marked
complete.
```

---

## Prompt 13 — Extraction manifest

```text
Create an extraction manifest for every extraction run.

Include:

run_id
source
requested_start
requested_end
actual_min_timestamp
actual_max_timestamp
event_count
partition_count
schema_hash
software_version
configuration_hash
checksums
completion status

Requirements:
- The manifest must allow exact identification of the dataset used in an
  experiment — i.e. given only a manifest, one must be able to determine
  precisely which data (down to partition/checksum level) an experiment
  used.
- Manifests must be immutable once marked complete; corrections require a
  new manifest, not an edit.
- Store manifests in a well-known, versioned location (e.g.
  `artifacts/manifests/<run_id>.json`) and index them so later phases can
  look up "the July manifest" and "the August manifest" unambiguously.

VALIDATION GATE: Generate a manifest for a real extraction run and show
that recomputing the checksum/schema_hash from the actual Parquet output
matches the manifest's recorded values exactly.
```

---

## Prompt 14 — July ingestion

```text
Implement the complete July ingestion command.

It must:

1. validate connection
2. discover source
3. extract July
4. write Parquet
5. checkpoint
6. generate manifest
7. generate basic quality statistics

Do not perform model training in this command — ingestion and training must
remain separately invokable stages.

Make it restartable end-to-end, not just at the extraction sub-step: if the
whole command is killed and re-run, it must detect already-completed
sub-steps (via manifests/checkpoints) and skip redundant work rather than
starting over.

At the end clearly report:
- events extracted
- duration
- throughput (events/sec)
- partitions written
- failures encountered (count and category)
- dropped events (count and reason codes)

VALIDATION GATE: Run the full July ingestion end-to-end on the real source,
then re-run it immediately after completion and show that the second run
detects everything is already done and exits quickly without re-extracting.
```

---

## Prompt 15 — August ingestion

```text
Implement the equivalent August ingestion pipeline, reusing the same
underlying ingestion machinery as July (do not fork a separate
implementation — parameterize by time range and manifest namespace).

August must be stored independently — separate partitions, separate
manifest, separate checkpoint namespace from July.

Do not allow August ingestion to modify July training artifacts — add an
explicit guard (e.g. a path/namespace check) that raises an error if August
ingestion code ever attempts to write into the July artifact tree.

Generate a separate manifest.

The code should make it difficult to accidentally mix July and August
datasets — e.g. dataset loaders should require an explicit `dataset=july|
august` parameter with no default, and cross-loading (loading August rows
into a function whose docstring/contract says "July only") should be
caught by a runtime assertion, not just convention.

VALIDATION GATE: Run August ingestion and show (a) it completes
independently of July's state, and (b) the July-write guard actually fires
if you deliberately point it at the July artifact path in a test.
```

---

# PHASE 2 — DATA QUALITY

## Prompt 16 — Canonical schema

```text
Create a versioned canonical event schema.

Include optional fields for:

event_id
timestamp
event.action
event.category
event.type
event.outcome
user.name
user.id
source.ip
source.port
destination.ip
destination.port
host.name
host.ip
process.name
process.command_line
process.parent.name
network.protocol
file.path
log.level
message
agent.id

Every field must have:
type
nullable (true/false)
normalization rule (how raw source values are transformed into this field)
source mapping (which discovered source fields, in priority order, populate
it)
validation rule (what makes a value valid vs. rejected/flagged)

Requirements:
- Encode the schema in a machine-readable form (e.g. a pydantic model or
  Arrow schema definition) that both the writer (Prompt 12) and validator
  (Prompt 20+) import from a single source of truth — do not duplicate the
  field list in multiple places.
- Version the schema explicitly (e.g. `schema_version: 1`) and store the
  version in every manifest, so future schema changes are traceable to the
  data they apply to.

VALIDATION GATE: Show the schema definition validating a handful of real
sample events end-to-end, including at least one event missing several
optional fields (to prove nullability is handled) and one malformed event
(to prove a validation rule actually rejects/flags it).
```

---

## Prompt 17 — Timestamp normalization

```text
Implement robust timestamp normalization.

Support common timestamp representations (ISO 8601 with/without
timezone, epoch millis/seconds, Elasticsearch's native date formats).

Convert internally to UTC with explicit timezone information (never a
naive/timezone-less datetime).

Preserve the original timestamp value alongside the normalized one, so
normalization is auditable/reversible for debugging.

Detect and separately count:
invalid timestamp (unparseable)
future timestamp (later than ingestion time, beyond a configurable
tolerance)
out-of-range timestamp (e.g. absurdly old, before the source system
existed)
duplicate timestamp (same entity + identical timestamp — not necessarily
an error, but must be observable in stats)

Do not silently discard invalid events — route them to a quarantine/
rejected-records store with the reason code, and count them in the
ingestion report from Prompt 14.

VALIDATION GATE: Feed a synthetic batch containing at least one example of
each detection category above and show the normalizer correctly classifies
and counts each one, with none silently disappearing.
```

---

## Prompt 18 — Event identity

```text
Implement deterministic event identity.

Prefer source document IDs (e.g. Elasticsearch `_id`) when available and
stable across re-extraction.

If unavailable, construct a stable fingerprint from an explicit, documented
set of event fields (e.g. a hash of timestamp + host + process + a
normalized message digest) — document exactly which fields are used and
why they were chosen to minimize both false collisions and false
uniqueness.

The ID must be deterministic across repeated extraction runs — re-
extracting the same time range twice must produce identical IDs for the
same underlying events.

Use it for deduplication (Prompt 19) and event-to-window mapping
(Prompt 22).

VALIDATION GATE: Extract the same small time range twice (two independent
runs) and show that the resulting event ID sets are identical, and that
event count and identity are stable across the two runs.
```

---

## Prompt 19 — Deduplication

```text
Implement scalable exact-event deduplication.

Perform it partition-wise (do not require a global in-memory hash set of
every event ID ever seen — use partition-local dedup plus, if needed, a
scalable approximate or on-disk structure for cross-partition dedup).

Report:

input count
duplicates found
retained count
duplicate ratio (%)

Do not remove legitimate repeated events — define precisely what counts as
a "duplicate" (identical event_id) versus a legitimately repeated event
(same content, different event_id/timestamp), and make this distinction
explicit and tested.

Keep deduplication configurable (on/off, and which identity strategy from
Prompt 18 to use).

VALIDATION GATE: Run dedup on a partition deliberately seeded with known
duplicate event IDs and known legitimately-repeated-but-distinct events,
and show the report correctly separates the two categories.
```

---

## Prompt 20 — Data quality report

```text
Build a scalable dataset profiler.

For July and August separately calculate:

event count
timestamp coverage (min/max/gaps)
missing-field percentages (per canonical field)
unique users
unique IPs
unique hosts
unique processes
event categories (distribution)
event outcomes (distribution)
daily volume
hourly volume
duplicate rate

Requirements:
- Use approximate cardinality (e.g. HyperLogLog via DuckDB) where appropriate
  for high-cardinality fields like unique IPs, rather than exact
  distinct-count over the full dataset if that would be prohibitively
  expensive at scale — document where approximate vs. exact counting is used
  and the expected error bound.
- Do not scan everything repeatedly unnecessarily — compute all profiler
  metrics in as few full-dataset passes as practical (e.g. one DuckDB query
  computing multiple aggregates at once, or a single Polars lazy pipeline).
- Output the report as a structured artifact (Parquet/JSON) plus a
  human-readable summary, timestamped and tied to the manifest of the
  dataset it profiles.

VALIDATION GATE: Produce and show the actual July and August quality
reports side by side, and flag any field with unexpectedly high missingness
(>20%, or another threshold you justify) for manual review before Phase 3
begins.
```

---

# PHASE 3 — 5-SECOND TEMPORAL ENGINE

## Prompt 21 — Window definition

```text
Implement the primary temporal window: 5 seconds.

For timestamp t:

window_start = floor(t to 5-second boundary)
window_end = window_start + 5 seconds

The window is the semantic unit of anomaly detection.

Internal processing chunks may have arbitrary sizes (e.g. reading 50,000
rows at a time for I/O efficiency), but the ML system must never interpret
"10,000 events" or any other I/O batch size as a temporal or semantic unit.

Requirements:
- Implement `window_start`/`window_end` as a pure, deterministic function of
  a UTC timestamp, unit-tested against edge cases: exact boundary
  timestamps (e.g. `12:00:00.000`), timestamps with sub-second precision,
  and timestamps at day/hour boundaries.
- Document this distinction (I/O batch vs. semantic window) explicitly in
  the windowing module's docstring, and add a lint/code-review checklist
  item: "does this code ever treat a batch size as a temporal boundary?"

VALIDATION GATE: Provide a table of at least 10 boundary-case timestamps
and their expected window_start/window_end, and show the implementation's
output matches exactly for all of them.
```

---

## Prompt 22 — Window assignment

```text
Assign every valid event:

event_id
window_id
window_start
window_end

Ensure deterministic assignment — the same event, processed twice, always
gets the same window_id.

Handle timezone normalization (all window math happens in UTC, per Prompt
17) and boundary conditions correctly (an event exactly at a 5-second
boundary belongs to the window that starts at that boundary, not the
preceding one — state and test this explicitly).

Write a compact event-window index (event_id → window_id mapping, plus
window-level summary) rather than duplicating complete event payloads into
a second copy of the full dataset.

VALIDATION GATE: Assign windows to a sample spanning a day boundary and a
DST-relevant date (if applicable to the source timezone) and show correct,
deterministic window assignment across both.
```

---

## Prompt 23 — Out-of-order events

```text
Design handling for out-of-order and late-arriving events.

Define:

allowed lateness (a configurable maximum delay after which a late event is
handled specially rather than silently included)
partition sorting strategy (how partitions are internally ordered to make
late-event detection efficient)
window finalization (the point at which a window is considered "closed" for
feature computation, and what happens to events arriving after that point)
late-event handling (e.g. routed to a separate "late events" store with
their original and intended window recorded, and a count reported)

The system must not use future information during inference — a window's
features must never depend on events that arrived, chronologically,
after that window was finalized during the actual detection run.

Document the chosen semantics clearly enough that a reader can determine,
for any given event, exactly which window (if any) it will be assigned to.

VALIDATION GATE: Construct a synthetic scenario with a deliberately
late-arriving event and show the pipeline correctly classifies it as late,
handles it per the documented policy, and does not retroactively alter an
already-finalized window's features.
```

---

## Prompt 24 — Empty windows

```text
Implement explicit handling of empty 5-second windows (windows with zero
events).

Determine and document whether empty windows should:

- be materialized (explicit rows with all-zero/null feature values)
- be represented implicitly (absent from the dataset, reconstructed on
  demand when needed for temporal continuity)
- contribute to temporal sequences (e.g. does the sequence model in Prompt
  45 need to "see" silence, or does silence get skipped?)

Do not simply discard them if doing so would distort temporal modelling —
e.g. if the sequence model relies on regular 5-second spacing, dropping
empty windows would corrupt the time axis.

Document the decision and its rationale, and make the choice a single
configurable point rather than an assumption baked into multiple modules
independently.

VALIDATION GATE: Show, on a real quiet time period (e.g. overnight), how
many empty windows exist, and demonstrate that the chosen representation
round-trips correctly through the windowing → feature → model pipeline
without silently vanishing or being double-counted.
```

---

## Prompt 25 — Temporal dataset builder

```text
Build the temporal dataset generation pipeline.

Input: canonical Parquet events (post schema-normalization and
deduplication).

Output: 5-second window dataset.

Each row represents one temporal window. Include:

window_id
start
end
event_count
entity cardinalities (distinct users/IPs/hosts/processes seen in the
window)
basic temporal metadata (e.g. position within day/hour, weekday)

Requirements:
- Make the output partitioned (e.g. by date, matching the raw layer) and
  efficient (streaming/lazy computation, not a full in-memory join of all
  events against all windows).
- This stage should be re-runnable independently of ingestion — given a
  fixed raw Parquet dataset, re-running window generation must be
  deterministic and idempotent.

VALIDATION GATE: Build the July window dataset end-to-end and cross-check:
sum of event_count across all windows equals the deduplicated valid event
count from the Prompt 20 quality report (accounting for any documented
late/quarantined events).
```

---

# PHASE 4 — FEATURE ENGINEERING

## Prompt 26 — Feature architecture

```text
Design a modular feature-engineering framework.

Every feature must have metadata:

name
group
source fields
mathematical definition
data type
expected range
missing-value behavior
training requirements (does it need July baseline stats to compute?)
causal/non-causal classification (does it ever reference data beyond the
current window and its past?)

Feature groups:

volume
users
IPs
hosts
processes
network
events
entropy
temporal
statistical
relationship novelty

Requirements:
- Implement features as a registry of small, independently testable
  functions/classes conforming to a common interface (e.g.
  `compute(window_data) -> dict[str, float]`), not as static security rules
  or ad hoc scripts.
- The causal/non-causal classification must be enforced, not just
  documented: features marked "causal" should be automatically testable by
  feeding them truncated data (up to time t) and confirming the output is
  identical to feeding the full dataset and only reading the value at t.

VALIDATION GATE: Register a trivial example feature end-to-end (definition
→ computation → causality test) to prove the framework works before
implementing the full feature groups in Prompts 27–35.
```

---

## Prompt 27 — Volume features

```text
Implement:

event_count
events_per_second
category_counts
action_counts
outcome_counts
authentication_volume
network_volume
process_volume
file_activity_volume

These are descriptive behavioural features — they characterize what
happened in a window, not whether it's anomalous.

Do not assign anomaly status directly in this module; volume features are
pure aggregations with no thresholding or scoring logic.

For each feature, specify exact source fields used and how missing/null
source values are counted (e.g. does a null `event.outcome` count toward
`outcome_counts` as "unknown" or get excluded?).

VALIDATION GATE: Compute volume features on a small hand-verifiable sample
window and manually confirm each value against a direct count of the raw
events in that window.
```

---

## Prompt 28 — User features

```text
Implement user behavioural features.

For each 5-second window derive:

active_users
user_event_concentration (e.g. Gini or Herfindahl-style concentration of
events across active users)
user diversity (e.g. count or entropy — cross-reference with Prompt 33)
login volume
failed-login ratio
user-host diversity
user-IP diversity
user-process diversity

Also support July-derived historical deviations — i.e. features that
compare a window's user behaviour against the frozen July baseline
(depends on Phase 5; stub this interface now, wire it up once baselines
exist).

Previously unseen users must not crash inference — explicitly test a
window containing a username never seen in July and confirm graceful
handling (e.g. treated as maximally novel, not a KeyError).

VALIDATION GATE: Run user features against a window containing at least
one unseen-user case and one all-known-users case, showing both complete
without error and produce sensible values.
```

---

## Prompt 29 — IP features

```text
Implement:

unique source IPs
unique destination IPs
source-IP concentration
destination diversity
internal/external proportions (requires a configurable internal-IP-range
definition, e.g. RFC1918 ranges, made explicit and overridable)
IP-user diversity
IP-host diversity
IP frequency relative to July
relationship novelty (has this exact IP-to-entity relationship been seen
in July?)

Do not automatically label a new IP as malicious — novelty features
produce a numeric evidence signal, not a boolean "bad IP" flag.

VALIDATION GATE: Test internal/external classification against a small set
of known internal and known external IPs to confirm the range logic is
correct, and confirm a genuinely novel IP produces a distinct novelty
signal without raising.
```

---

## Prompt 30 — Host features

```text
Implement:

unique hosts
host activity
host-user diversity
host-IP diversity
host-process diversity
host event-category distribution
host historical frequency
host relationship novelty

Follow the same missing/unseen-entity handling standard established in
Prompts 28–29: unseen hosts must be handled gracefully and consistently
with how unseen users/IPs are handled, using the same shared novelty
utility rather than a separate ad hoc implementation.

VALIDATION GATE: Confirm via a shared unit test suite that unseen-entity
handling is behaviorally identical in shape (not values) across user, IP,
and host features — i.e. they all use the same underlying novelty
mechanism from Prompt 26's framework.
```

---

## Prompt 31 — Process features

```text
Implement:

unique processes
process activity
process-host relationships
process-user relationships
parent-child relationships
command-line pattern diversity (define precisely what "pattern" means —
e.g. tokenized/normalized command-line shape, not raw string equality,
since raw command lines often contain unique arguments like timestamps or
random ports)
process historical frequency

Do not maintain a malicious-process blacklist as the detector — process
features describe behavioural shape and frequency, not identity-based
threat lists.

VALIDATION GATE: Show command-line pattern normalization on a handful of
real example command lines (e.g. differing only by a PID or temp file
name) and confirm they normalize to the same pattern, while genuinely
different commands normalize differently.
```

---

## Prompt 32 — Network features

```text
Implement:

network event volume
unique destinations
unique destination ports
protocol diversity
source-destination diversity
connection concentration
network entropy
host-network relationships

Cross-check consistency with the IP features from Prompt 29 — e.g. "unique
destinations" here and "unique destination IPs" there should use the same
underlying field mapping and counting logic, not duplicated/divergent
implementations.

VALIDATION GATE: Run both IP features (Prompt 29) and network features on
the same sample window and confirm overlapping metrics (e.g. unique
destination IP counts) agree exactly.
```

---

## Prompt 33 — Entropy

```text
Implement Shannon entropy for appropriate categorical distributions.

H(X) = -Σ p(x) log2 p(x)

Apply to:

users
IPs
hosts
processes
destinations
protocols
event categories

Handle:
empty distributions (zero events in the window — define entropy as 0, null,
or NaN, pick one and document it, and be consistent)
single-value distributions (entropy = 0 by definition — must be exact, not
a near-zero floating point artifact of an edge case in the formula)
high-cardinality distributions (many near-uniform categories — verify
numerical stability, e.g. no log(0) errors, no overflow)

Benchmark computational cost of entropy computation at realistic
per-window cardinality and report whether it is a meaningful fraction of
total feature-computation time at scale.

VALIDATION GATE: Unit test entropy against hand-computed values for at
least: an empty window, a single-category window, a two-category
50/50-split window (expected H=1 bit), and a uniform 4-category window
(expected H=2 bits).
```

---

## Prompt 34 — Temporal features

```text
Implement causal temporal features:

previous-window event count
event-rate change (vs. previous window(s))
user-count change
IP-count change
host-count change
process-count change
inter-event statistics (e.g. mean/variance of inter-arrival time within
the window)
burstiness (a defined burstiness statistic, e.g. Fano factor or coefficient
of variation of inter-event times — specify which one and why)
time since previous activity (per relevant entity, e.g. per host or per
user)

All features must be causal — every one of these must be computable using
only the current window and windows strictly before it in time. Add this
as an explicit causality unit test per feature (reuse the framework from
Prompt 26).

VALIDATION GATE: Run the causality test suite from Prompt 26 against every
feature implemented in this prompt and show 100% pass before proceeding.
```

---

## Prompt 35 — Multi-scale context

```text
Keep 5 seconds as the primary window but calculate causal rolling context
over:

30 seconds
1 minute
5 minutes
15 minutes

Never use future windows — every rolling aggregate at window w must only
incorporate windows at or before w.

Document exactly how each rolling feature is computed: window alignment
(trailing, not centered), handling of empty sub-windows within the rolling
range (per the Prompt 24 decision), and the exact aggregation function
(mean/sum/std/etc.) per feature.

Benchmark the cost of maintaining four parallel rolling scales at full
data volume, and consider (and document the decision on) whether these are
computed via a single streaming rolling-window pass or via repeated
DuckDB/Polars window functions.

VALIDATION GATE: Run the same causality test methodology as Prompt 34
against a sample of the multi-scale rolling features, and additionally
test a rolling window's value at the very start of the dataset (where
fewer than the full rolling range of history exists) to confirm it degrades
gracefully rather than erroring or leaking padding as if it were real data.
```

---

# PHASE 5 — JULY BASELINE

## Prompt 36 — Baseline architecture

```text
Design a persistent July baseline system.

It must learn only from July — add a runtime guard (not just a code
convention) that raises an error if any baseline-fitting function is ever
called with data whose timestamps fall outside the configured July range.

Baseline categories:

global distributions
user distributions
IP distributions
host distributions
process distributions
relationship frequencies
feature statistics
temporal statistics

The baseline must be versioned and immutable after training: once a
baseline artifact is written and marked "frozen," no code path may modify
it in place; any change produces a new version with a new id, and the
inference pipeline (Phase 8) must reference an explicit baseline version,
never "latest."

VALIDATION GATE: Demonstrate the July-only runtime guard actually fires by
attempting (in a test) to fit a baseline component with a small amount of
August-range data mixed in, and confirm it raises rather than silently
proceeding.
```

---

## Prompt 37 — Frequency baselines

```text
Calculate July frequency distributions for:

users
IPs
hosts
processes
user-IP
user-host
host-process
IP-host
process-command

Support high-cardinality data efficiently.

Do not load enormous dictionaries into memory if unnecessary — evaluate
appropriate approximate structures (e.g. count-min sketch, or an
on-disk/DuckDB-backed frequency table) for the highest-cardinality
relationships (likely user-IP, IP-host, process-command), and justify the
choice per relationship type based on its expected cardinality.

VALIDATION GATE: Benchmark memory usage of frequency-baseline construction
at full July scale (or a scaled-down proxy with documented extrapolation)
and show it stays within a defined, justified memory budget rather than
scaling linearly and unboundedly with unique entity count.
```

---

## Prompt 38 — Statistical baselines

```text
Calculate July:

mean
std
median
MAD (median absolute deviation)
IQR (interquartile range)
percentiles (specify which — e.g. p50/p90/p95/p99/p99.9)

Use robust statistics (median/MAD/IQR) for heavy-tailed features rather
than relying solely on mean/std, and document per-feature which statistics
are actually used downstream for calibration vs. which are computed only
for reporting/diagnostics.

Persist the statistics in an efficient artifact format (e.g. Parquet or a
compact structured format), keyed by feature name and versioned per Prompt
36.

VALIDATION GATE: For at least one known heavy-tailed feature (e.g. event
count per window, which is likely highly skewed), show both the
mean/std and the robust (median/MAD) summary side by side, and explain
which one downstream calibration (Prompt 39) will use and why.
```

---

## Prompt 39 — Baseline feature transformation

```text
Implement transformations using July distributions:

percentile (where does a value fall in the July percentile distribution?)
robust z-score (using median/MAD instead of mean/std)
IQR distance (how far outside [Q1-k·IQR, Q3+k·IQR] is a value?)
frequency rarity (how rare is this entity/relationship in the July
frequency baseline?)
tail distance (distance into the extreme tail relative to July's observed
range)

Every transformation must be fitted on July — the fitting step (computing
percentile boundaries, robust stats, frequency tables) happens once against
frozen July baselines.

August only applies the frozen transformation — August feature values are
looked up against/mapped through the already-fitted July transformation,
never used to refit or adjust it. Enforce this the same way as Prompt 36's
guard: the "apply" function must be structurally incapable of also fitting.

VALIDATION GATE: Show a concrete worked example: take one real July
baseline distribution, fit each transformation, then apply the fitted
transformation to a hand-picked August-like value and confirm the output
matches a manual calculation.
```

---

## Prompt 40 — Baseline validation

```text
Validate the July baseline.

Check:

stability across July days (do frequency/statistical baselines look
similar if computed on, say, the first half vs. second half of July, or do
they shift significantly — indicating July itself may not be a stable
"normal" period?)
extreme sensitivity (do a small number of outlier July events distort the
baseline disproportionately — e.g. does one noisy host dominate host
frequency stats?)
high-cardinality behavior (do rare entities get reasonable treatment, or
does the baseline degenerate for the long tail?)
missing-value behavior (how do baseline stats handle windows/entities with
missing feature values?)
distribution coverage (does the July baseline actually span a representative
range of normal operational conditions — weekday/weekend, business hours/
off hours, etc.?)

Produce a baseline quality report summarizing all the above with concrete
numbers/plots data (even if only described in text/tables here), not just
a pass/fail statement.

Do not inspect August for baseline tuning — this validation is entirely
July-internal (e.g. July split into two halves), never referencing August
data even for sanity-checking purposes.

VALIDATION GATE: Present the baseline quality report and explicitly flag
any instability found (e.g. "host frequency baseline shifts by X% between
July weeks 1-2 vs 3-4") before proceeding to Phase 6. If instability is
found, propose a mitigation (e.g. longer baseline window, robust
statistics) rather than silently proceeding.
```

---

# PHASE 6 — UNSUPERVISED MODELS

## Prompt 41 — Model interface

```text
Create a common anomaly detector interface:

fit()
score()
predict()
explain()
save()
load()

Input: window-level feature matrix (the output of Phase 4, optionally
transformed via Phase 5 baselines).

Output: per-window results, at minimum:

raw_score (the model's native output, whatever scale it naturally produces)
calibrated_evidence (see Phase 6/7 calibration — must be comparable across
detectors, unlike raw_score)
anomaly (a boolean or graded flag derived from calibrated_evidence and a
frozen threshold, not from raw_score directly)
model_version

Requirements:
- `fit()` must only ever be called with July data (enforce via the same
  guard pattern as Prompt 36).
- `save()`/`load()` must round-trip exactly: a loaded model must produce
  identical `score()` output to the model instance immediately after
  `fit()`, for the same input.

VALIDATION GATE: Implement the interface with a trivial dummy detector
(e.g. one that scores based on event_count alone) and demonstrate the full
fit → save → load → score round-trip test passes before implementing real
detectors.
```

---

## Prompt 42 — Isolation Forest

```text
Implement Isolation Forest as the first baseline detector.

Train exclusively on July.

Document:

n_estimators
max_samples
max_features
contamination (note: since this is unsupervised discovery, treat
`contamination` carefully — document whether/how it's used, since setting
it based on assumed anomaly rate is itself an assumption worth being
explicit about)
random_state
n_jobs

Do not claim the raw score is a probability — Isolation Forest's raw
anomaly score is a relative ranking signal, not a calibrated probability;
say so explicitly in code comments and documentation.

Do not use min-max normalization (per the global prohibition in Prompt 1/2)
— any rescaling of the raw score must use July-fitted robust statistics
(Prompt 38/39), not the min/max of the current scoring batch.

Persist the model and preprocessing (the exact feature transformation
pipeline used to produce its input) together as one versioned artifact, so
a loaded model always knows exactly what preprocessing to expect.

VALIDATION GATE: Fit on July, score a July validation split, and show the
raw score distribution (e.g. histogram/percentiles) to confirm it produces
a sensible spread rather than degenerate output (e.g. everything scoring
identically).
```

---

## Prompt 43 — Isolation Forest calibration

```text
Calibrate Isolation Forest anomaly evidence using July only.

Use empirical score distributions and quantiles (map raw scores to, e.g.,
"this score falls at the Xth percentile of July's own score
distribution") rather than an arbitrary fixed cutoff.

Investigate score stability across July days — does the raw-score-to-
evidence mapping computed from, say, the first half of July generalize
reasonably to the second half? If not, note it as a limitation.

Create frozen thresholds (a specific evidence level above which a window
is flagged), stored as a versioned calibration artifact tied to the model
version from Prompt 42.

Explain mathematically what the resulting evidence means (e.g. "evidence
of 0.95 means this window's raw score exceeds 95% of July windows' raw
scores").

Do not use August for any part of calibration.

VALIDATION GATE: Show the full raw-score → percentile → evidence →
threshold pipeline applied to a July validation split, and report what
fraction of July validation windows get flagged at the chosen threshold
(this should be roughly consistent with expectations for "normal" data,
and any large deviation should be investigated and explained).
```

---

## Prompt 44 — Autoencoder

```text
Implement an unsupervised PyTorch autoencoder.

Train only on July.

Use a chronological July validation split (i.e. split July by time, e.g.
earlier days for training / later days for validation, not a random
shuffle-split, since shuffling would let the model "see" the future
relative to some training windows — even within July this matters for a
temporal system).

Track:

training loss
validation loss
reconstruction error distribution

Calibrate reconstruction-error thresholds from July, using the same
empirical-quantile approach established in Prompt 43 for consistency
across detectors.

Persist model, preprocessing and configuration (architecture, learning
rate, epochs, seed) together as one versioned artifact.

VALIDATION GATE: Show a training/validation loss curve (as data/table, even
if not plotted visually) demonstrating the model is actually learning
(validation loss decreasing and stabilizing, not diverging or flat from
epoch 1), and confirm training used only July data via a timestamp-range
assertion in the training script.
```

---

## Prompt 45 — Temporal sequence model

```text
Implement a sequence-based unsupervised model.

Input: consecutive 5-second feature windows (a sequence, respecting the
Phase 3/24 decision on empty-window representation so the sequence has
consistent temporal spacing).

Objective: learn normal temporal transitions (e.g. predict the next
window's features from a preceding sequence, or reconstruct a sequence,
depending on the chosen architecture — specify which).

Train only on July, with the same chronological-split discipline as Prompt
44.

Ensure no future information leakage: at no point during training does a
predicted/reconstructed window at position t have access to ground-truth
data from position >t within the same training example.

Return per-window temporal anomaly evidence, following the same
raw_score/calibrated_evidence pattern as Prompts 42–44.

Benchmark whether the sequence model actually improves detection over
independent-window models — this requires the benchmarking framework from
Prompt 49; if that doesn't exist yet, define a minimal comparison here
(e.g. compare July-validation reconstruction/prediction quality against a
naive "predict-the-mean" baseline) and defer the full comparison to Prompt
49.

VALIDATION GATE: Demonstrate the no-leakage property with an explicit test:
show that changing a window's data at position t+1 has zero effect on the
model's output for position t.
```

---

# PHASE 7 — DETECTOR ENSEMBLE

## Prompt 46 — Statistical detector

```text
Implement a robust statistical anomaly detector based on July feature
distributions.

Use deviation from frozen July baselines (leverage Prompt 39's
transformations — e.g. robust z-score / IQR distance / tail distance —
combined into a per-window statistical evidence score, with the combination
method explicitly documented, e.g. max deviation across features, or a
weighted sum).

Do not create hardcoded attack thresholds — any threshold used must be
derived from July's own empirical distribution (per Prompt 43's
methodology), not a fixed number chosen from domain intuition about what
"looks bad."

Return feature-level evidence (which specific features drove the score,
useful later for explanation in Prompt 55) and window-level evidence (the
combined score).

VALIDATION GATE: Run the statistical detector on a July validation window
with a known, deliberately-injected extreme feature value and confirm both
the window-level score reflects it and the feature-level breakdown
correctly attributes it to the injected feature.
```

---

## Prompt 47 — Rarity detector

```text
Implement learned rarity features based on July (leveraging the frequency
baselines from Prompt 37).

Previously unseen relationships should generate measurable novelty
evidence but must NOT automatically equal maliciousness — the detector's
output is a rarity/novelty score, and any language in code, logs, or
reports must avoid framing novelty as inherently bad.

Integrate rarity as model evidence rather than a static rule — i.e. it
should feed into the same evidence/calibration pattern as other detectors
(Prompts 42–46), not act as an independent hard-coded gate that overrides
other signals.

VALIDATION GATE: Show a window containing a genuinely novel relationship
(e.g. a user-host pair never seen in July) produces elevated rarity
evidence, while a window with only previously-seen relationships produces
low rarity evidence — using real or realistic synthetic data.
```

---

## Prompt 48 — PCA detector

```text
Implement PCA reconstruction anomaly detection.

Fit exclusively on July.

Determine dimensionality (number of retained components) using July
validation (e.g. explained-variance threshold or reconstruction-error
elbow on a held-out July split), not an arbitrary fixed number.

Calibrate reconstruction thresholds using July, via the same empirical-
quantile methodology as other detectors.

Benchmark against Isolation Forest and Autoencoder (requires Prompt 49's
framework — at minimum, compare July-validation score distributions and
flagged-window rates across the three).

VALIDATION GATE: Report the chosen number of principal components, the
explained variance at that count, and show reconstruction error on a
July validation split is roughly stable/well-behaved (no pathological
blow-up).
```

---

## Prompt 49 — Model benchmark

```text
Create a July-only model benchmarking framework.

Compare:

Isolation Forest
Autoencoder
Sequence model
Statistical detector
PCA
Rarity representation

Measure:

training time
inference time
memory
score stability (e.g. how consistent is a detector's July-validation
flagged rate across different July validation slices?)
daily anomaly rate (per detector, per July validation day — flag any
detector whose rate is wildly unstable day to day)
feature sensitivity (which features most influence each detector's score,
so downstream explanation makes sense)

Do not use August to choose the winner — all comparison and selection here
uses July training/validation splits exclusively; August remains untouched
until Phase 8.

DELIVERABLE: a benchmark report table (detector | train time | inference
time | memory | July-validation flagged rate | stability notes).

VALIDATION GATE: Produce the actual benchmark table from real runs (not
placeholder numbers) and identify at least one detector, if any, that
shows pathological behavior (e.g. flags near 0% or near 100% of windows) —
investigate and either fix or explicitly exclude it from the ensemble with
justification.
```

---

## Prompt 50 — Ensemble design

```text
Design a principled ensemble.

Do NOT average incompatible raw scores (an Isolation Forest raw score and
an autoencoder reconstruction error are on different, non-comparable
scales — averaging them directly is not meaningful).

First calibrate each detector's output using July empirical distributions
(reuse Prompt 43's percentile-based calibration approach uniformly across
all detectors, so every detector's "evidence" is on the same 0–1 (or
similar) comparable scale before combination).

Then combine evidence — investigate multiple combination methods (e.g.
mean of calibrated evidence, max, a learned/weighted combination validated
on July, or a voting/agreement-based scheme) and select using July
validation stability (does the combined evidence produce a stable,
sensible flagged-rate on July validation data, consistent with Prompt 49's
findings?).

Document the mathematics precisely: given calibrated evidence values
e_1...e_n from n detectors, state the exact formula used to produce the
final ensemble evidence.

VALIDATION GATE: Show the calibrated (not raw) evidence distributions from
at least three detectors on the same July validation set side by side,
confirm they're on comparable scales, then show the combined ensemble
evidence distribution and justify the chosen combination method against at
least one alternative you tried and rejected.
```

---

# PHASE 8 — UNSEEN ANOMALY DISCOVERY

## Prompt 51 — Define anomaly

```text
Formalize:

statistical anomaly (a precise definition — e.g. feature value(s) with low
probability under the July-fitted distribution)
behavioural anomaly (a pattern of feature values, possibly individually
unremarkable, that is jointly unusual)
temporal anomaly (an unusual transition or sequence, as flagged by the
sequence model)
novel relationship (an entity-pair or relationship never observed in July)
distributional drift (a population-level shift between July and August,
distinct from a single-window anomaly — cross-reference Prompt 59)
model disagreement (detectors substantially disagree on a window's
evidence)
potential security relevance (a qualitative, human-facing judgment
category — explicitly distinct from all the above, since none of the
above categories alone implies security relevance)

Do not equate anomaly with attack anywhere in this taxonomy or its
downstream usage — every definition above describes statistical/
behavioural unusualness, not intent or maliciousness.

DELIVERABLE: create an evidence taxonomy document that every later phase
(especially Phase 9's episodes and Phase 12's reports) references by name,
so "anomaly," "novelty," and "drift" are never used loosely or
interchangeably in later output.

VALIDATION GATE: Review the taxonomy against the actual detector outputs
built in Phases 6–7 and confirm every detector's evidence output maps
cleanly to at least one category in the taxonomy — if a detector's output
doesn't fit any category, refine the taxonomy rather than forcing a
mismatch.
```

---

## Prompt 52 — August blind inference

```text
Implement the August inference pipeline.

Load:

July schema (exact version)
July feature definitions (exact version)
July preprocessing (exact fitted transformation, per Prompt 39)
July baseline (exact frozen artifact, per Prompt 36)
July models (exact versioned artifacts, per Prompts 42–48)
July calibrators (exact fitted calibration, per Prompt 43/50)
July thresholds (exact frozen values)

Do not update any of them — the inference pipeline must load these as
strictly read-only artifacts; there is no "online learning" or "adaptive
threshold" behavior anywhere in this stage.

Process August 5-second windows through the identical feature-computation
code path used for July (same functions, different data — not a
reimplementation), to guarantee feature-computation logic itself cannot
differ between July and August.

Produce anomaly evidence for every August window (not just ones that
exceed a threshold — the full evidence distribution over all of August is
needed for later drift and rate analysis).

VALIDATION GATE: Before running full August inference, run it on a tiny
August sample and verify by inspection that every loaded artifact's
version/id matches the exact July artifacts intended, with no accidental
use of a stale or wrong-version artifact.
```

---

## Prompt 53 — Model disagreement

```text
For every August window calculate:

detector outputs (calibrated evidence from each of the detectors in
Phases 6–7)
detector agreement (a defined agreement metric — e.g. how many detectors
independently flag this window above their respective thresholds)
detector disagreement (the inverse — e.g. variance/spread of calibrated
evidence across detectors)
dominant detector (which detector contributed the most evidence to this
window, if the ensemble combination method makes that identifiable)
ensemble evidence (the Prompt 50 combined score)

Use this for investigation and diagnostics, not as a hardcoded security
rule — e.g. do not add logic like "if disagreement > X, automatically
downgrade severity" without that being an explicit, documented,
justified design decision reviewed alongside the rest of the methodology.

VALIDATION GATE: Show the per-window disagreement breakdown for at least
one high-ensemble-evidence August window and one low-evidence window, and
confirm the numbers are internally consistent (e.g. dominant detector's
individual evidence really is the highest among detectors for that
window).
```

---

## Prompt 54 — Anomaly ranking

```text
Rank August windows by ensemble anomaly evidence.

For each top window show:

timestamp
event count
model evidence (ensemble)
detector evidence (per-detector breakdown, from Prompt 53)
top feature deviations (which features contributed most, using the
statistical/rarity detectors' feature-level output from Prompts 46–47)
baseline comparison (how this window's key features compare to July
baseline norms)
novel relationships (any new entity relationships present, from Prompt 47)
temporal context (surrounding windows' evidence, to see if this is
isolated or part of a burst — feeds into Phase 9)

VALIDATION GATE: Produce the actual ranked list for real August data (or
the largest available real sample) and manually sanity-check the top 5
entries — do their feature deviations and evidence breakdowns make
narrative sense together, or does anything look like a pipeline bug (e.g.
a feature deviation that doesn't match the raw event data when you check
it directly)?
```

---

## Prompt 55 — Event attribution

```text
For anomalous windows, trace back to contributing events.

Implement defensible event attribution: given a window with high ensemble
evidence and specific feature deviations, identify which underlying raw
events in that window most plausibly drove those specific feature values.

Do not claim causal attribution unless justified — e.g. if a window's
elevated "unique destination IPs" feature is driven by 40 distinct
connection events, attribution can defensibly point to all 40 events, but
if the anomaly is a distributional/statistical property of the whole
window, do not falsely narrow attribution to a single event without
support.

Provide for each attributed event:
event ID
event timestamp
relevant fields (only the fields relevant to the specific triggering
feature(s), not the entire raw event dump indiscriminately)
associated anomalous features (which feature(s) this event contributed to)
attribution method (which logic/rule produced this attribution)
attribution confidence (a stated, reasoned confidence level, not a bare
number without justification)

VALIDATION GATE: Run attribution on the top-ranked window from Prompt 54
and manually verify that the attributed events, when read directly, really
do explain the flagged feature deviations.
```

---

# PHASE 9 — ANOMALY EPISODES

## Prompt 56 — Temporal grouping

```text
Group consecutive or related anomalous 5-second windows into anomaly
episodes.

Calculate:

start
end
duration
number of windows
peak evidence
mean evidence
affected users
affected IPs
affected hosts
affected processes
model agreement (episode-level aggregation of Prompt 53's per-window
agreement)

Define precisely what "consecutive or related" means (e.g. windows within
N seconds of each other and both above a minimum evidence floor; document
N and the floor, and justify them using July-validation false-positive-rate
considerations rather than an arbitrary guess).

VALIDATION GATE: Run episode grouping on the ranked August windows from
Prompt 54 and show at least one multi-window episode's full detail,
confirming the aggregated stats (peak/mean evidence, affected entities)
match manual recomputation from the constituent windows.
```

---

## Prompt 57 — Persistent anomalies

```text
Analyze whether anomalies:

occur once
repeat (same entities, non-contiguous episodes)
persist (a single long episode)
escalate (evidence trending upward across an episode or across repeats)
recur periodically (a detectable periodicity, e.g. same time each day)

Do not use static attack rules to make this classification — use temporal
evidence directly (episode timestamps, evidence trends, entity overlap
across episodes) computed from the data itself.

VALIDATION GATE: Show at least one real example from each classification
category found in the August data (or explicitly state if a category
genuinely has zero examples, rather than forcing a weak match into an
empty category).
```

---

## Prompt 58 — Novel behaviour

```text
Identify August behaviour that was not represented in July.

Investigate:

new entities (users/IPs/hosts/processes never in July)
new relationships (entity-pairs never in July)
new temporal patterns (e.g. activity at a time-of-day never seen in July)
rare process behaviour
rare user behaviour
rare network behaviour

Do not automatically classify novelty as malicious — this stage produces
observations, feeding into the model-only candidate pipeline (Prompt 60),
not verdicts.

VALIDATION GATE: Produce a concrete inventory (counts and examples) of new
entities/relationships found in real August data relative to the frozen
July baseline, and cross-check a sample manually against raw July data to
confirm they genuinely didn't appear (ruling out a baseline-lookup bug).
```

---

## Prompt 59 — Drift

```text
Perform separate distribution-drift analysis between July and August.

Identify features whose distribution changed (e.g. via a distributional
distance/statistical test comparing July's fitted distribution to August's
observed distribution, per feature).

Clearly distinguish:

population drift (a broad, dataset-wide shift — e.g. overall event volume
increased across the board)
operational change (a plausible, identifiable non-anomalous cause — e.g. a
new host was legitimately onboarded)
individual anomaly (a localized, specific-window/episode deviation, not a
population-wide shift)

Do not confuse global August drift with individual threats — e.g. if
overall event volume in August is 20% higher than July across nearly all
windows, that is drift, not 20% of August being individually anomalous;
the anomaly-scoring pipeline (Phase 8) should already be somewhat robust to
this via percentile-based calibration, but this analysis exists specifically
to catch and flag cases where it isn't.

VALIDATION GATE: Report which features (if any) show significant July→
August drift, and for each one, state explicitly whether it appears to be
population drift, an operational change, or a signal worth flagging as
methodologically important context for interpreting Phase 8's results.
```

---

## Prompt 60 — Model-only anomalies

```text
Create the most important investigation pipeline.

Identify anomalies discovered by our model that are NOT already
represented by existing monitoring alerts, when corresponding alert data is
available (i.e. cross-reference August anomaly episodes against existing
Elastic/Kibana alert data for the same time range/entities, if accessible
read-only).

Call them:

MODEL-ONLY CANDIDATE ANOMALIES

Never call them confirmed attacks automatically — every output artifact,
log message, and report referencing these must use the phrase
"model-only candidate anomaly" or equivalent, never "attack," "intrusion,"
or "confirmed threat."

For every candidate produce complete evidence and context: episode detail
(Prompt 56), event attribution (Prompt 55), novelty context (Prompt 58),
drift context (Prompt 59), and explicit confirmation that no matching
existing alert was found in the comparison window.

VALIDATION GATE: Produce the actual list of model-only candidates from real
August data (or state clearly if none exist, which is itself a valid and
important scientific finding — do not manufacture candidates to have
something to show), along with the alert-comparison methodology used to
rule out existing-monitoring overlap.
```

---

# PHASE 10 — EVALUATION

## Prompt 61 — July chronological validation

```text
Split July chronologically into training and validation periods.

Use early July for fitting.

Use later July for:

hyperparameter selection
threshold calibration
feature stability
model comparison

Never use August for any of the above — this prompt's entire scope is
July-internal validation, executed and finalized before Phase 8's August
inference begins.

VALIDATION GATE: Document the exact chronological split point(s) used
(e.g. "July 1–21 train, July 22–31 validate") and confirm via a manifest/
config artifact that every fitting/calibration step in Phases 5–7 actually
used only the training portion, with validation reserved exclusively for
the checks listed above.
```

---

## Prompt 62 — Frozen experiment

```text
Create a formal experiment artifact:

EXPERIMENT_ID

Store:

training dataset manifest (link to Prompt 13's July manifest)
validation dataset manifest (the July validation split's manifest)
August dataset manifest (link to Prompt 13's August manifest)
feature version (Prompt 26's registry version)
model versions (Prompts 42–48's artifact versions)
configuration hash (hash of the full resolved config used)
random seeds (every seed used anywhere in the pipeline)
thresholds (frozen calibration thresholds, Prompt 43/50)
software versions (dependency versions, code commit hash)

Freeze all July artifacts before August inference begins — the experiment
artifact should be created and marked "frozen" as the explicit boundary
between "July work" and "August work" in the project's history.

VALIDATION GATE: Show that, given only the EXPERIMENT_ID artifact, someone
else could locate every single dependency (data, features, models,
thresholds, code version) needed to exactly reproduce the experiment,
without needing any additional undocumented context.
```

---

## Prompt 63 — August statistics

```text
Generate August results:

total windows
anomalous windows (at the frozen threshold)
anomaly percentage
daily anomaly rate
hourly anomaly rate
episode count
top anomaly evidence

Detect pathological detector behavior such as almost everything being
anomalous (or, conversely, almost nothing being flagged, which is equally
worth catching) — define an explicit sanity range (e.g. "if flagged rate
exceeds 15% or falls below 0.01%, treat this as a methodology red flag
requiring investigation before trusting the results," with the specific
numbers justified by your July-validation flagged rates from Prompt 43/49).

VALIDATION GATE: Produce the actual August statistics from real inference
output and explicitly state whether they fall within the sanity range; if
not, do not proceed to present results as valid findings — investigate the
pipeline first.
```

---

## Prompt 64 — Candidate validation

```text
Create a human validation mechanism.

Analyst labels should support:

BENIGN
EXPECTED_CHANGE
SUSPICIOUS
SECURITY_RELEVANT
UNKNOWN

Do not alter the original model output when an analyst label is applied —
labels are stored as a separate, append-only annotation layer keyed to
episode/window/candidate IDs, never overwriting the model's original
evidence or classification.

Store annotations separately (e.g. their own Parquet/table), with analyst
identity, timestamp, and optional free-text notes, so the annotation
history itself is auditable.

VALIDATION GATE: Demonstrate the annotation mechanism end-to-end on at
least one real model-only candidate from Prompt 60: apply a label, confirm
the original model evidence artifact is byte-for-byte unchanged, and
confirm the annotation is retrievable and correctly linked.
```

---

## Prompt 65 — Existing monitoring comparison

```text
If Elastic/Kibana alert data is available, compare it with model results.

Produce:

both detected (existing alert and model both flagged the same time/
entity)
Elastic-only (existing alert fired, model did not flag)
model-only (model flagged, no existing alert — these are the Prompt 60
candidates)
neither (informational baseline — not usually reported individually, but
useful for computing overall rates)

The research focus is MODEL-ONLY candidates — this comparison exists
primarily to identify and validate that set, not to produce a general
"our model vs. Elastic" scoreboard.

Do not claim model superiority unless supported by validated evidence —
any summary statement comparing the two systems must be grounded in the
analyst-labeled outcomes from Prompt 64 (e.g. "of N model-only candidates,
M were analyst-labeled SECURITY_RELEVANT or SUSPICIOUS"), not raw counts
alone, since a high model-only count with all candidates later labeled
BENIGN is not evidence of superiority.

VALIDATION GATE: Produce the actual four-way comparison table from real
data (or the largest available real sample with existing alert data), and
if analyst labels from Prompt 64 exist yet, report the labeled breakdown of
the model-only set; if not, explicitly flag that superiority claims cannot
yet be made pending analyst review.
```

---

# PHASE 11 — SCALE

## Prompt 66 — Large-scale benchmark

```text
Benchmark the pipeline on progressively larger datasets.

Measure at:

10K
100K
1M
10M
100M
representative billion-scale workload where feasible (if a true
billion-scale run isn't feasible in this environment, extrapolate from the
100M measurement with a clearly stated methodology and confidence caveat)

Measure at each scale:

ingestion throughput (events/sec)
Parquet throughput (write and read, MB/sec and events/sec)
feature generation throughput (windows/sec)
model inference throughput (windows/sec)
RAM (peak, not just average)
CPU (utilization)
GPU (utilization, where applicable)
disk usage (raw vs. derived artifact sizes)

Identify bottlenecks: for each scale tier, state which stage is the
limiting factor and why (I/O bound, CPU bound, memory bound).

VALIDATION GATE: Produce the actual benchmark table across all achievable
scales (real measurements, not estimates, for every tier that was actually
run) and identify the single largest bottleneck standing between current
performance and the target billion-scale workload.
```

---

## Prompt 67 — Distributed processing

```text
Evaluate whether the feature-generation and inference stages should use:

Polars
DuckDB
PyArrow
Dask
Ray
Spark

or another distributed approach.

Do not add distributed technology unnecessarily — justify any addition
specifically against the bottleneck(s) identified in Prompt 66, not in the
abstract.

Benchmark first: before adopting any new distributed tool, show a
before/after benchmark on a representative workload proving it actually
resolves the identified bottleneck and by how much.

Select the simplest architecture that reliably handles the real dataset —
if single-machine Polars/DuckDB with sensible chunking already clears the
target scale within acceptable time/resource budgets, do not add
Dask/Ray/Spark merely for architectural sophistication.

VALIDATION GATE: Present the before/after benchmark comparison for
whatever decision is made (including "no change needed, single-machine
tools already suffice at target scale, here's the evidence") before
implementing any change.
```

---

## Prompt 68 — GPU optimization

```text
Benchmark GPU acceleration where useful.

Evaluate GPU usage for:

autoencoder (training and inference)
sequence model (training and inference)
feature computation where supported (e.g. any GPU-accelerable numeric
transforms)

Do not force GPU usage into stages where CPU/Arrow processing is faster —
e.g. feature engineering over categorical/string-heavy data is often
faster on CPU with Polars/DuckDB than moved to GPU; only use GPU where
benchmarked to help.

Document actual measured improvement (CPU time vs. GPU time, including
data-transfer overhead, for each evaluated stage) — a GPU path that's
theoretically faster but net-slower once transfer overhead is included
should be rejected and the rejection documented.

VALIDATION GATE: Show the actual CPU-vs-GPU benchmark numbers for each
evaluated stage and state the final decision (GPU or CPU) per stage with
the measured justification.
```

---

## Prompt 69 — Fault tolerance

```text
Test:

network interruption (mid-extraction)
Elasticsearch timeout
process crash (kill -9 mid-stage)
machine restart
disk-full condition
corrupt partition (simulate a truncated/corrupted Parquet file)
incomplete checkpoint (simulate a checkpoint write interrupted partway)

The pipeline must recover safely without silently duplicating or losing
data for every scenario above — for each one, define and test the expected
recovery behavior explicitly (resume from checkpoint, quarantine the
corrupt partition and alert, fail loudly and require manual intervention,
etc.) rather than leaving recovery behavior undefined.

VALIDATION GATE: Run each of the seven fault scenarios as an actual test
(simulated, not just reasoned about) against the real pipeline code, and
show the observed recovery behavior for each, confirming no silent data
loss or duplication occurred (verify via event counts/checksums pre- and
post-recovery).
```

---

## Prompt 70 — Full reproducibility

```text
Run the entire July→August experiment twice using identical artifacts and
seeds.

Compare outputs.

The results should be deterministic within documented numerical tolerance
(state the tolerance explicitly — e.g. "model scores must match to within
1e-6" for floating-point model outputs, exact match for counts/IDs/
rankings).

Investigate every discrepancy — any value that differs between the two
runs beyond the stated tolerance must be root-caused (e.g. unseeded
randomness somewhere, nondeterministic parallel aggregation order) and
either fixed or the source of nondeterminism explicitly documented as a
known, accepted limitation.

VALIDATION GATE: Present a diff report between the two full runs' outputs
(manifests, model artifacts, evidence scores, rankings, episode lists) and
show either full determinism or a fully explained, bounded list of
tolerated discrepancies.
```

---

# PHASE 12 — RESULTS + DASHBOARD

## Prompt 71 — Research result generator

```text
Generate the final experiment results package.

Include:

dataset statistics (from Prompt 20)
feature statistics (from Phase 4/5)
model comparison (from Prompt 49)
July validation (from Prompt 61)
August detection (from Prompt 63)
anomaly episodes (from Prompt 56)
model-only candidates (from Prompt 60)
drift (from Prompt 59)
performance benchmarks (from Phase 11)

Export machine-readable results (e.g. a structured Parquet/JSON bundle),
tied to the frozen EXPERIMENT_ID from Prompt 62, so the entire results
package is traceable to one specific, reproducible experiment run.

VALIDATION GATE: Show the generated results package validates against a
schema (i.e. every expected section is present and non-empty, or
explicitly and legitimately empty with a stated reason) before treating it
as final.
```

---

## Prompt 72 — Top anomaly report

```text
Generate a Top-100 August anomaly report.

For every candidate include:

rank
timestamp
duration
ensemble evidence
detector agreement
top anomalous features
July comparison
novel relationships
affected entities
related events
model-only status (per Prompt 60/65)
analyst status (per Prompt 64, if labeled yet)

Export JSON, Parquet and Markdown — the Markdown version should be
directly human-readable (a proper report, not a raw data dump), while
JSON/Parquet remain the machine-readable source of truth.

VALIDATION GATE: Produce the actual Top-100 report from real August
results (or the largest available real result set if fewer than 100
qualifying candidates exist — do not pad the list) in all three formats,
and spot-check that the Markdown rendering accurately reflects the
underlying structured data for at least 3 entries.
```

---

## Prompt 73 — Minimal Streamlit

```text
Build only a simple Streamlit investigation dashboard.

Do not perform heavy processing in Streamlit — the app must only read
precomputed Parquet/results artifacts generated by Prompts 71–72; it must
contain zero model inference, feature computation, or heavy aggregation
logic of its own.

Read precomputed Parquet/results.

Display:

overview (dataset stats, August anomaly rate)
anomaly timeline
top anomaly episodes
model-only candidates
individual case details (drill-down into a single episode's full evidence/
attribution)
feature deviations
related events
July comparison
analyst annotation (read and, if desired, write new annotations via the
Prompt 64 mechanism — but writing annotations is the only mutation this UI
performs; it must never write to model/feature/baseline artifacts)

The UI must never become part of the ML pipeline — reinforce this with a
code-organization rule: the Streamlit app package has no import dependency
on the ingestion/windowing/feature/model/inference modules' internals,
only on the finalized results artifacts' read interface.

VALIDATION GATE: Confirm by inspecting imports that the Streamlit app
cannot execute any ingestion, feature computation, or model
fitting/inference code paths, only reads and (for annotations only)
appends to already-generated artifacts.
```

---

## Prompt 74 — End-to-end production run

```text
Run the complete experiment from scratch.

Pipeline:

Kibana
→ July Parquet
→ validation
→ 5-second windows
→ features
→ July baseline
→ July training
→ July validation
→ model calibration
→ artifact freeze
→ August Parquet
→ August windows
→ August features
→ frozen inference
→ anomaly ranking
→ episode reconstruction
→ model-only candidate identification
→ final reports

Do not skip validation at any stage — every validation gate defined in
Prompts 1–73 must actually execute (not be commented out or bypassed for
speed) as part of this end-to-end run.

Stop if leakage, schema mismatch or artifact inconsistency is detected —
the run must fail loudly and clearly at the first point such an issue is
detected, rather than continuing with degraded/invalid intermediate state.

Produce a complete experiment manifest (the Prompt 62 EXPERIMENT_ID
artifact, now fully populated with real run data end to end).

VALIDATION GATE: Execute this full run for real, capture the complete
console/log output, and show the final experiment manifest plus a
statement confirming every validation gate along the way passed (or, if
any failed and required a fix, document what failed and how it was
resolved before the run completed successfully).
```

---

## Prompt 75 — Final scientific audit

```text
Perform a complete scientific and engineering audit of the entire project.

The central research question is:

"Can an unsupervised temporal anomaly detection system trained only on
July cybersecurity behaviour identify previously unseen anomalous
behaviour in August, including potentially important model-only anomalies
that existing monitoring did not surface?"

Audit every stage, answering each question below with a specific,
evidence-backed answer (cite the specific artifact/test/report from
Prompts 1–74 that supports the answer — do not answer any of these from
memory or assumption):

DATA:
- Was July completely isolated from August?
- Was August ever used for training?
- Were August statistics used for thresholds?
- Are timestamps correct?
- Are duplicate events controlled?
- Is the extraction reproducible?

TEMPORAL:
- Are exactly 5-second windows used?
- Are internal I/O batches incorrectly influencing semantics?
- Are rolling features causal?
- Is future information leaking into current features?
- Are late events handled correctly?

FEATURES:
- Are all features mathematically defined?
- Are baseline statistics trained only on July?
- Are rare/unseen entities handled correctly?
- Are feature transformations frozen?
- Are any features accidentally using August information?

MODELS:
- Are models genuinely unsupervised?
- Are models trained only on July?
- Are thresholds calibrated only on July?
- Are raw scores being incorrectly interpreted as probabilities?
- Is min-max normalization avoided?
- Are detector scores properly calibrated before ensemble fusion?

ENSEMBLE:
- Are incompatible raw scores being averaged?
- Is ensemble methodology statistically justified?
- Is model disagreement preserved?

UNSEEN ANOMALIES:
- Are anomalies actually unseen relative to July?
- Are model-only candidates properly identified?
- Are anomalies being incorrectly called attacks?
- Is there enough evidence to investigate them?

SCALABILITY:
- Can the system process the real dataset?
- What is the bottleneck?
- Is memory bounded?
- Are Parquet partitions efficient?
- Can processing resume after failure?

REPRODUCIBILITY:
- Can the same experiment be reproduced?
- Are artifacts versioned?
- Are dataset manifests stored?
- Are configuration hashes stored?

Finally produce a complete final report with these sections:

1. System architecture
2. Exact mathematical pipeline
3. Feature inventory
4. Model inventory
5. Training methodology
6. Threshold methodology
7. August inference methodology
8. Unseen anomaly methodology
9. Model-only anomaly methodology
10. Performance benchmarks
11. Detection results
12. Top candidate anomalies
13. Limitations
14. Known failure modes
15. Recommended next experiments

Be scientifically honest.

If the system does NOT yet demonstrate that it finds meaningful unseen
anomalies, explicitly say so, and explain specifically why (weak signal,
insufficient July baseline period, high false-positive rate, unresolved
leakage risk, etc.) rather than framing a negative or inconclusive result
as a success.

Do not fabricate successful detection results. Every claim in the final
report must be traceable to a specific artifact, benchmark, or test output
produced somewhere in Prompts 1–74 — if a claim cannot be traced this way,
remove it or explicitly label it as an untested hypothesis for future work.

VALIDATION GATE: This audit is itself the final validation gate for the
entire project. Do not consider the project complete until every checklist
question above has a specific, evidenced answer, and the final report is
produced with all 15 sections populated from real, traceable project
artifacts.
```

---

# Notes carried over unchanged from the original

- **Do not delete the old project.** Keep this as a completely independent
  research implementation. If the new system turns out to be substantially
  better, you can later decide whether anything from it should be
  integrated into the existing SOC platform.
- **Development order matters more than tool count.** Don't start with five
  or six ML algorithms at once — build in this order: data extraction →
  data correctness → 5-second windows → feature correctness → July baseline
  → Isolation Forest baseline → evaluate methodology → autoencoder →
  temporal model → ensemble. If a complex multi-model system produces
  something strange, you need to be able to isolate where the problem is.
- **Demonstrable CLI output beats a dashboard for convincing a mentor.**
  Being able to run `ingest july`, `windows july`, `features july`,
  `train july`, and `detect august` from the terminal and show real,
  correct numbers at each stage is more credible than a polished UI.
- **No CSV. No static rules. No current-batch min-max score. No arbitrary
  10,000-event semantic batches. No training on August.**
