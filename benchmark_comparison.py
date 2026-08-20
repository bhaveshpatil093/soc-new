"""
Validation benchmark comparing Model-identified anomalies against legacy Elastic alerts.

Explicitly enforces that model superiority claims cannot be made without
analyst-labeled evidence (SECURITY_RELEVANT/SUSPICIOUS) from the AnnotationStore.
"""

from __future__ import annotations

import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from tabulate import tabulate

from tads.investigation.annotations import AnnotationLabel, AnnotationStore


@dataclass
class MockAlert:
    id: str
    start_time: datetime
    end_time: datetime


def main() -> None:
    # 1. Generate Mock 4-Way Data
    # Let's say we have 10,000 total background windows
    total_windows = 10000

    # We'll measure in "events/episodes" for simplicity, but map them to rough window counts

    # Both Detected (Model caught it, Elastic caught it)
    both_episodes = [MockAlert("BOTH-1", datetime(2025, 8, 1, 10, 0, tzinfo=UTC), datetime(2025, 8, 1, 10, 5, tzinfo=UTC))]

    # Elastic-Only (Signature matched, Model didn't care)
    elastic_only_episodes = [
        MockAlert("ELAS-1", datetime(2025, 8, 1, 11, 0, tzinfo=UTC), datetime(2025, 8, 1, 11, 2, tzinfo=UTC)),
        MockAlert("ELAS-2", datetime(2025, 8, 1, 12, 0, tzinfo=UTC), datetime(2025, 8, 1, 12, 2, tzinfo=UTC)),
    ]

    # Model-Only (The true Candidates)
    model_only_episodes = [
        MockAlert("MOD-1", datetime(2025, 8, 1, 13, 0, tzinfo=UTC), datetime(2025, 8, 1, 13, 10, tzinfo=UTC)),
        MockAlert("MOD-2", datetime(2025, 8, 1, 14, 0, tzinfo=UTC), datetime(2025, 8, 1, 14, 15, tzinfo=UTC)),
        MockAlert("MOD-3", datetime(2025, 8, 1, 15, 0, tzinfo=UTC), datetime(2025, 8, 1, 15, 5, tzinfo=UTC)),
    ]

    # Rough window conversions (assuming 1 window = 1 episode for this summary table)
    count_both = len(both_episodes)
    count_elastic_only = len(elastic_only_episodes)
    count_model_only = len(model_only_episodes)
    count_neither = total_windows - (count_both + count_elastic_only + count_model_only)

    print("\n" + "=" * 60)
    print("=== MODEL VS ELASTIC: 4-WAY COMPARISON ===")
    print("=" * 60)

    table = [
        ["Both Detected", count_both, "Flagged by Model & Elastic"],
        ["Elastic-Only", count_elastic_only, "Existing signature alert fired, model ignored"],
        ["Model-Only", count_model_only, "Model flagged, no existing alert (Candidates)"],
        ["Neither", count_neither, "Informational background baseline"],
    ]
    print(tabulate(table, headers=["Category", "Count (Episodes)", "Description"], tablefmt="grid"))

    # 2. Check Annotation Store to validate Model-Only candidates
    print("\n=== VALIDATION GATE: ANALYST VERIFICATION ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = os.path.join(tmpdir, "annotations.jsonl")
        store = AnnotationStore(storage_path=store_path)

        # Scenario A: No labels exist yet
        print("\n[Scenario A: Pending Review]")
        # We query the empty store
        labels_found = False
        for ep in model_only_episodes:
            if store.get_history(ep.id):
                labels_found = True

        if not labels_found:
            print("⚠️  WARNING: Superiority claims CANNOT yet be made pending analyst review.")
            print("The model-only candidates exist, but lack human ground-truth validation.")

        # Scenario B: Analyst labels are applied
        print("\n[Scenario B: Post-Review (Simulated)]")
        # Pre-populate some labels
        store.append(model_only_episodes[0].id, "candidate", AnnotationLabel.SECURITY_RELEVANT, "alice")
        store.append(model_only_episodes[1].id, "candidate", AnnotationLabel.SUSPICIOUS, "bob")
        store.append(model_only_episodes[2].id, "candidate", AnnotationLabel.BENIGN, "charlie")

        # Aggregate labels
        label_counts = defaultdict(int)
        validated_threats = 0

        for ep in model_only_episodes:
            history = store.get_history(ep.id)
            if history:
                latest_label = history[-1].label
                label_counts[latest_label.value] += 1
                if latest_label in (AnnotationLabel.SECURITY_RELEVANT, AnnotationLabel.SUSPICIOUS):
                    validated_threats += 1

        print(f"\nOf {count_model_only} model-only candidates, {validated_threats} were analyst-labeled SECURITY_RELEVANT or SUSPICIOUS.")

        print("\nLabeled Breakdown:")
        for label, count in label_counts.items():
            print(f"  - {label}: {count}")

        if validated_threats > 0:
            print("\n✅ SUCCESS: Model superiority (identifying true blind-spots) is supported by validated evidence.")
        else:
            print("\n❌ FAILURE: High model-only count with 0 confirmed threats. Model is generating false positives.")


if __name__ == "__main__":
    main()
