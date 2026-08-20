"""
TADS Investigation Dashboard — Streamlit App

IMPORT BOUNDARY RULE
────────────────────
This file imports ONLY from:
  • Python stdlib
  • streamlit, pandas, json  (third-party UI/data)
  • dashboard.data            (our thin artifact-reader layer)

It has ZERO imports from any tads.* package.  It performs ZERO model
inference, feature computation, or heavy aggregation.  The only mutation
is appending analyst annotations via dashboard.data.save_annotation().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path so `dashboard` is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import streamlit as st

from dashboard.data import (
    load_experiment_results,
    load_top100_parquet,
    load_top100_json,
    load_annotations,
    save_annotation,
)

# ── Page Config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TADS Investigation Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared CSS ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .metric-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border-radius: 12px; padding: 1.2rem; text-align: center;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .metric-card h3 { color: #a78bfa; margin: 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-card p  { color: #f1f5f9; margin: 0.3rem 0 0; font-size: 1.6rem; font-weight: 700; }
    .verdict-tp { color: #ef4444; font-weight: 700; }
    .verdict-fp { color: #22c55e; font-weight: 700; }
    .verdict-pending { color: #facc15; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ── Data Loading (cached) ─────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _load_all():
    exp = load_experiment_results()
    df = load_top100_parquet()
    detail = load_top100_json()
    return exp, df, detail


exp_results, top100_df, top100_detail = _load_all()
annotations = load_annotations()   # not cached — must reflect writes


# ── Sidebar ────────────────────────────────────────────────────────────────

st.sidebar.title("🛡️ TADS Dashboard")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Anomaly Timeline", "Top Episodes",
     "Model-Only Candidates", "Case Drill-Down"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption(
    f"Experiment: **{exp_results['experiment_id']}**  \n"
    f"Git: `{exp_results['metadata']['git_commit'][:10]}…`"
)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ═══════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.title("Experiment Overview")

    ds = exp_results["dataset_statistics"]
    perf = exp_results["performance_benchmarks"]

    # Metric cards
    cols = st.columns(4)
    cards = [
        ("Total Events", f"{ds['total_events']:,}"),
        ("Unique Users", str(ds["unique_users"])),
        ("Unique Hosts", str(ds["unique_hosts"])),
        ("Baseline Period", f"{ds['time_range_days']:.0f} days"),
    ]
    for col, (label, val) in zip(cols, cards):
        col.markdown(
            f'<div class="metric-card"><h3>{label}</h3><p>{val}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # August anomaly rate
    total_august_windows = 5000  # from our synthetic dataset
    anomalous = len(top100_df)
    rate = anomalous / total_august_windows * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("August Windows Scored", f"{total_august_windows:,}")
    c2.metric("Anomalies (≥0.90 evidence)", str(anomalous))
    c3.metric("Anomaly Rate", f"{rate:.2f}%")

    st.markdown("---")

    # Model comparison table
    st.subheader("Model Comparison")
    mc = pd.DataFrame(exp_results["model_comparison"])
    st.dataframe(mc, use_container_width=True, hide_index=True)

    # Performance
    st.subheader("Performance Benchmarks")
    p1, p2 = st.columns(2)
    p1.metric("Ingestion Throughput", f"{perf['ingestion_throughput_eps']:,.0f} events/sec")
    p2.metric("Inference Latency", f"{perf['inference_ms_per_window']:.2f} ms/window")

    # Drift
    drift = exp_results["drift"]
    if drift["detected"]:
        st.warning(f"⚠️ Drift detected in: **{', '.join(drift['drifted_features'])}**")
    else:
        st.success("✅ No feature drift detected between July and August.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Anomaly Timeline
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Anomaly Timeline":
    st.title("August Anomaly Timeline")

    chart_df = top100_df[["timestamp", "ensemble_evidence", "category"]].copy()
    chart_df = chart_df.sort_values("timestamp")

    st.scatter_chart(
        chart_df,
        x="timestamp",
        y="ensemble_evidence",
        color="category",
        height=420,
    )

    # Category distribution
    st.subheader("Category Distribution")
    cat_counts = top100_df["category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    st.bar_chart(cat_counts, x="Category", y="Count", horizontal=True)

    # Evidence distribution
    st.subheader("Evidence Distribution")
    st.bar_chart(top100_df["ensemble_evidence"].value_counts(bins=20).sort_index())


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Top Episodes
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Top Episodes":
    st.title("Top Anomaly Episodes")

    episodes = exp_results.get("anomaly_episodes", [])
    if not episodes:
        st.info("No pre-computed episodes in the results bundle.")
    else:
        for ep in episodes:
            with st.expander(
                f"🔴 {ep['episode_id']}  |  {ep['start_time']} → {ep['end_time']}  |  "
                f"Evidence: {ep['max_evidence']:.2f}  |  Windows: {ep['window_count']}",
                expanded=True,
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Max Evidence", f"{ep['max_evidence']:.4f}")
                c2.metric("Window Count", ep["window_count"])
                c3.metric("Category", ep["primary_category"])

    st.markdown("---")
    st.subheader("Top-100 Ranked Anomalies")
    display_cols = ["rank", "timestamp", "ensemble_evidence", "category",
                    "related_events", "model_only_status"]
    st.dataframe(
        top100_df[display_cols].head(20),
        use_container_width=True,
        hide_index=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Model-Only Candidates
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Model-Only Candidates":
    st.title("Model-Only Candidates")
    st.caption(
        "Windows flagged by unsupervised ML detectors that would NOT have been "
        "caught by rule-based or frequency-based methods alone."
    )

    model_only_df = top100_df[top100_df["model_only_status"] == True].copy()

    if model_only_df.empty:
        st.info("No model-only candidates in the current result set.")
    else:
        st.metric("Model-Only Candidates", len(model_only_df))
        st.dataframe(
            model_only_df[["rank", "timestamp", "ensemble_evidence",
                           "category", "related_events"]],
            use_container_width=True,
            hide_index=True,
        )

    # Also show from experiment bundle
    st.markdown("---")
    st.subheader("From Experiment Bundle")
    exp_candidates = exp_results.get("model_only_candidates", [])
    if exp_candidates:
        st.dataframe(pd.DataFrame(exp_candidates), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Case Drill-Down
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Case Drill-Down":
    st.title("Case Drill-Down")

    selected_rank = st.selectbox(
        "Select anomaly by rank",
        options=top100_df["rank"].tolist(),
        format_func=lambda r: f"#{r} — {top100_df[top100_df['rank']==r]['timestamp'].iloc[0]} "
                              f"(Evidence: {top100_df[top100_df['rank']==r]['ensemble_evidence'].iloc[0]:.4f})",
    )

    row = top100_df[top100_df["rank"] == selected_rank].iloc[0]
    detail = top100_detail[selected_rank - 1]  # 0-indexed list

    # Header
    st.markdown(f"## #{row['rank']}  —  {row['timestamp']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evidence", f"{row['ensemble_evidence']:.4f}")
    c2.metric("Category", row["category"] or "—")
    c3.metric("Events", row["related_events"])
    c4.metric("Model-Only", "Yes" if row["model_only_status"] else "No")

    st.markdown("---")

    # ── Detection Profile ──────────────────────────────────────────────
    st.subheader("Detection Profile")
    agreed = row["detector_agreement"]
    st.markdown(f"**Detectors agreed:** {', '.join(agreed)}  ({len(agreed)} / 6)")
    st.markdown(f"**Top features:** {row['top_anomalous_features']}")

    # ── Feature Deviations / July Comparison ───────────────────────────
    st.subheader("Feature Deviations — July Baseline Comparison")
    july_comp = row["july_comparison"]
    comp_rows = []
    for feat, vals in july_comp.items():
        comp_rows.append({
            "Feature": feat,
            "August Value": f"{vals['val']:.2f}",
            "July Median": f"{vals['median']:.2f}",
            "Ratio": f"{vals['ratio']:.2f}x",
        })
    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

    # ── Affected Entities ──────────────────────────────────────────────
    st.subheader("Affected Entities")
    entities = row["affected_entities"]
    e1, e2 = st.columns(2)
    e1.metric("User", entities["user"])
    e2.metric("Host", entities["host"])

    # ── Novel Relationships ────────────────────────────────────────────
    novel = row["novel_relationships"]
    if novel:
        st.subheader("Novel Relationships")
        for nr in novel:
            st.markdown(f"- {nr}")

    # ── Related Events ─────────────────────────────────────────────────
    st.subheader("Related Events")
    st.markdown(f"**{row['related_events']}** events observed in this window.")

    # ── Analyst Annotation ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🏷️ Analyst Annotation")

    ts_key = str(row["timestamp"])
    existing = annotations.get(ts_key, {})

    verdict_options = ["Pending", "True Positive", "False Positive", "Needs Review"]
    current_verdict = existing.get("verdict", "Pending")
    current_notes = existing.get("notes", "")

    with st.form(key=f"annotation_{selected_rank}"):
        verdict = st.selectbox(
            "Verdict",
            verdict_options,
            index=verdict_options.index(current_verdict) if current_verdict in verdict_options else 0,
        )
        notes = st.text_area("Notes", value=current_notes, height=100)
        submitted = st.form_submit_button("Save Annotation", type="primary")
        if submitted:
            save_annotation(ts_key, verdict, notes)
            st.success(f"✅ Annotation saved for {ts_key}")
            st.rerun()

    if existing:
        cls = {"True Positive": "verdict-tp", "False Positive": "verdict-fp"}.get(
            existing.get("verdict", ""), "verdict-pending"
        )
        st.markdown(
            f'Current verdict: <span class="{cls}">{existing.get("verdict", "Pending")}</span>  \n'
            f'Last updated: {existing.get("updated_at", "—")}',
            unsafe_allow_html=True,
        )
