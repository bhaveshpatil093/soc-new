# Evidence Taxonomy

> **Canonical Reference Document — Version 1.0**
>
> All downstream phases (Phase 9 episodes, Phase 12 reports, explanation
> pipelines) MUST reference this taxonomy by name. The terms defined below
> are the **only** permitted vocabulary for describing detector outputs.
> Using "anomaly", "novelty", or "drift" loosely or interchangeably is
> explicitly prohibited.

---

## Foundational Principle

> [!IMPORTANT]
> **No category in this taxonomy implies maliciousness, intent, or attack.**
> Every definition below describes *statistical or behavioural unusualness*
> relative to a frozen July baseline. A window classified under any of
> these categories may be entirely benign. The mapping from evidence
> categories to security relevance is a separate, human-facing judgment
> step documented at the end of this file.

---

## 1. Evidence Categories

### 1.1 Statistical Anomaly

**Definition.** A window in which one or more individual feature values
have low probability under the July-fitted marginal distribution for that
feature.

**Formal criterion.** Feature value $x_j$ in window $W$ is a statistical
anomaly with respect to feature $j$ if its robust z-score
$|x_j - \tilde{x}_j| / \text{MAD}_j$ exceeds the empirical $p$-th
percentile of July's own robust z-score distribution for feature $j$,
where $p$ is a frozen calibration threshold.

**Key property.** This is a *per-feature, per-window* judgment. The
features are evaluated independently; joint unusualness is covered by
*Behavioural Anomaly* below.

**Producing detector(s):** `RobustStatisticalDetector`

**What it is NOT.** A statistical anomaly does not mean the value is
"wrong" or "malicious." Many legitimate operational events (maintenance
windows, software deployments, batch jobs) produce statistically unusual
feature values.

---

### 1.2 Behavioural Anomaly

**Definition.** A window in which the *joint configuration* of feature
values is unusual, even if each individual feature value is unremarkable
in isolation.

**Formal criterion.** A window $W$ with feature vector
$\mathbf{x} = (x_1, x_2, ..., x_d)$ is a behavioural anomaly if the
model's reconstruction or density score for $\mathbf{x}$ exceeds the
empirical $p$-th percentile of July's own score distribution.

**Key property.** This captures multivariate structure — correlations,
co-occurrences, and density regions — that univariate tests miss. A
window where every feature is individually at the 70th percentile but
their *combination* is at the 99.5th percentile is a behavioural anomaly
but not a statistical anomaly.

**Producing detector(s):**
- `IsolationForestDetector` (multivariate density)
- `AutoencoderDetector` (learned nonlinear reconstruction)
- `PCADetector` (linear subspace reconstruction)

**What it is NOT.** A behavioural anomaly does not mean the system is
misbehaving. It means the system is doing something it rarely did during
July, which may simply reflect legitimate new usage patterns.

---

### 1.3 Temporal Anomaly

**Definition.** A window whose feature values represent an unusual
*transition* relative to the preceding sequence of windows, even if the
window's features would be unremarkable in isolation.

**Formal criterion.** Given a sequence of windows
$W_{t-k}, ..., W_{t-1}$, the temporal anomaly score for window $W_t$ is
the prediction error $\| \hat{\mathbf{x}}_t - \mathbf{x}_t \|^2$, where
$\hat{\mathbf{x}}_t$ is the model's prediction of $W_t$ given only the
causal context $W_{t-k}, ..., W_{t-1}$. This error is calibrated against
July's own prediction-error distribution.

**Key property.** This is inherently sequential. A window that would be
perfectly normal in a random sample can be a temporal anomaly if it
follows an unexpected predecessor. The model is strictly causal: the
prediction for time $t$ uses only information from times $< t$.

**Producing detector(s):** `SequenceLSTMDetector`

**What it is NOT.** A temporal anomaly does not mean "something bad
happened at this moment." It means the system's behaviour changed in a
way that was unpredicted by its recent history — which may simply be a
legitimate shift in workload.

---

### 1.4 Novel Relationship

**Definition.** A window containing a categorical entity or
entity-relationship (e.g., user-host pair, process name) that was never
observed in the July training data.

**Formal criterion.** A categorical value $v$ in feature $j$ within
window $W$ is novel if $v \notin \text{Vocab}_j^{\text{July}}$. The
novelty score is the information-theoretic surprisal
$-\log P_{\text{July}}(v)$, where unseen values are assigned a floor
probability of $1/N_{\text{July}}$.

**Key property.** This is a *categorical-domain* concept. It applies
specifically to discrete entity identifiers and their co-occurrence
patterns, not to continuous feature magnitudes.

**Producing detector(s):** `RarityDetector`

**What it is NOT.** A novel relationship is **not** inherently
malicious. New employees, new servers, software updates, and
infrastructure changes routinely create genuinely novel relationships
that are entirely benign. Novelty is an *observational fact*, not a
*security verdict*.

---

### 1.5 Distributional Drift

**Definition.** A population-level shift in the distribution of feature
values or entity frequencies between the July baseline period and a
subsequent observation period (e.g., August).

**Formal criterion.** Distributional drift is measured at the
*population* level (across many windows), not at the *window* level. It
is detected by comparing aggregate statistics (e.g., rolling medians,
frequency tables, distribution quantiles) between the July baseline and
a rolling August window. Standard tests include the
Kolmogorov–Smirnov statistic, Population Stability Index (PSI), or
divergence of rolling robust statistics from July baselines.

**Key property.** Drift is explicitly **distinct** from a single-window
anomaly. A single unusual window is a Statistical, Behavioural, or
Temporal Anomaly. Drift is a systematic shift affecting *many* windows,
potentially rendering the July baseline stale.

**Producing detector(s):** Phase 8 drift monitoring (cross-reference
Prompt 59). Not produced by any single-window Phase 6/7 detector.

**What it is NOT.** Drift does not mean the system is under attack. It
means the operational baseline has shifted — possibly due to legitimate
infrastructure changes, seasonal workload patterns, or organic growth.
Drift is a *model health* signal, not a *security* signal.

---

### 1.6 Model Disagreement

**Definition.** A window for which the calibrated evidence values from
different detectors are substantially inconsistent.

**Formal criterion.** Given calibrated evidence values
$e_1, e_2, ..., e_n$ from $n$ detectors for window $W$, model
disagreement is present when:

$$\max(e_1, ..., e_n) - \min(e_1, ..., e_n) > \delta$$

where $\delta$ is a frozen disagreement threshold derived from July's
own evidence-spread distribution.

**Key property.** Model disagreement is an *epistemic uncertainty*
signal. It indicates that the ensemble's sub-models have conflicting
views about the window. This can indicate:
- The window lies in a region of feature space where only one detector
  has learned structure (legitimate orthogonality).
- The anomaly is domain-specific (e.g., purely categorical, hence only
  the Rarity detector fires).

**Producing detector(s):** `EnsembleDetector` (computed from the spread
of its sub-detector evidence values).

**What it is NOT.** Disagreement is not itself an anomaly. It is a
meta-signal about detector confidence. High disagreement with high max
evidence suggests a domain-specific anomaly. High disagreement with low
max evidence is likely noise.

---

### 1.7 Potential Security Relevance

**Definition.** A qualitative, human-facing judgment category indicating
that a window or episode *may* warrant security investigation, based on
the conjunction of evidence categories above and domain context.

**Formal criterion.** There is no formal statistical criterion. This
category is assigned by a downstream triage or explanation module
(Phase 12) based on:
- The specific evidence categories triggered.
- The magnitude and consistency of the evidence.
- Domain heuristics (e.g., novel relationships involving privileged
  accounts are more concerning than novel relationships involving
  service accounts performing routine discovery).

**Key property.** This is the **only** category in this taxonomy that
involves a judgment about security. All preceding categories are purely
descriptive of statistical or behavioural properties.

**Producing detector(s):** None. This category is produced by the
human-facing explanation and triage layer (Phase 12), not by any
automated detector.

**What it is NOT.** Potential security relevance is **not** a confirmed
attack. It is a recommendation for human review.

---

## 2. Detector → Taxonomy Mapping

The following table confirms that every detector built in Phases 6–7
maps cleanly to at least one evidence category:

| Detector                   | Primary Category       | Secondary Category    |
|----------------------------|------------------------|-----------------------|
| `RobustStatisticalDetector`| Statistical Anomaly    | —                     |
| `IsolationForestDetector`  | Behavioural Anomaly    | —                     |
| `AutoencoderDetector`      | Behavioural Anomaly    | —                     |
| `PCADetector`              | Behavioural Anomaly    | —                     |
| `SequenceLSTMDetector`     | Temporal Anomaly       | —                     |
| `RarityDetector`           | Novel Relationship     | —                     |
| `EnsembleDetector`         | *(combination)*        | Model Disagreement    |
| Phase 8 Drift Monitor      | Distributional Drift   | —                     |
| Phase 12 Triage            | Potential Security Relevance | —              |

> [!NOTE]
> Every Phase 6/7 detector's evidence output maps cleanly to exactly one
> primary category. The `EnsembleDetector` is a meta-detector that
> combines calibrated evidence from the primary detectors; its secondary
> output is the model disagreement signal derived from the spread of
> sub-detector evidence values.

---

## 3. Usage Rules

1. **Never use "anomaly" without a qualifier.** Always specify
   *statistical anomaly*, *behavioural anomaly*, or *temporal anomaly*.
   The bare word "anomaly" is ambiguous and prohibited in reports.

2. **Never equate anomaly with attack.** Every report, log message, and
   code comment must maintain the distinction between evidence
   (statistical unusualness) and judgment (potential security relevance).

3. **Never use "novelty" and "drift" interchangeably.** Novelty is a
   single-window, categorical-domain observation. Drift is a
   population-level, temporal phenomenon.

4. **Always cite the producing detector.** When referencing an evidence
   category in a report, cite the specific detector that produced the
   evidence so the reader can trace the signal back to its source.

5. **Distributional Drift is a model-health signal.** It should be
   reported separately from per-window anomaly evidence, since it
   describes the validity of the baseline, not the properties of a
   single window.
