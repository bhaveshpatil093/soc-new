"""
Validation benchmark for the Human Annotation Mechanism.

Proves that analyst labels can be successfully applied, stored, and retrieved
while strictly preserving the byte-for-byte integrity of the original
model inference artifacts.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime

from tads.explanation.episodes import AnomalyEpisode
from tads.investigation.annotations import AnnotationLabel, AnnotationStore
from tads.investigation.candidates import ModelOnlyCandidate


def get_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def main() -> None:
    print("=== Generating Mock Model-Only Candidate ===")

    ep = AnomalyEpisode(
        episode_id="EP-999-MOCK",
        start_time=datetime(2025, 8, 1, 12, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 8, 1, 12, 5, 0, tzinfo=UTC),
        duration_seconds=300.0,
        window_count=60,
        peak_evidence=0.9999,
        mean_evidence=0.9500,
        affected_users={"alice"},
    )

    candidate = ModelOnlyCandidate(
        episode=ep,
        attribution_data={"feature": "f_volume", "events": 500},
        temporal_context=["persist", "escalate"],
        drift_context=["f_volume: Population Drift"],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Save original inference artifact
        artifact_path = os.path.join(tmpdir, "candidate_EP-999-MOCK.json")
        with open(artifact_path, "w", encoding="utf-8") as f:
            # A simple manual serialization since dataclasses with datetimes need a default encoder
            data = {
                "episode_id": candidate.episode.episode_id,
                "peak_evidence": candidate.episode.peak_evidence,
                "clearance": candidate.alert_clearance_statement,
            }
            json.dump(data, f)

        # 2. Hash the artifact BEFORE annotation
        original_hash = get_file_hash(artifact_path)
        print(f"Original Artifact SHA-256: {original_hash}")

        # 3. Apply human annotation
        print("\n=== Applying Human Validation Label ===")
        store_path = os.path.join(tmpdir, "annotations.jsonl")
        store = AnnotationStore(storage_path=store_path)

        print("Analyst 'charlie' applies SECURITY_RELEVANT label to EP-999-MOCK.")
        store.append(
            target_id=candidate.episode.episode_id,
            target_type="candidate",
            label=AnnotationLabel.SECURITY_RELEVANT,
            analyst="charlie",
            notes="Observed massive data exfiltration pattern.",
        )

        # 4. Retrieve annotation
        print("\n=== Retrieving Annotation History ===")
        history = store.get_history(candidate.episode.episode_id)
        assert len(history) == 1
        retrieved = history[0]

        print(f"Retrieved Label: {retrieved.label.value}")
        print(f"Analyst: {retrieved.analyst}")
        print(f"Notes: {retrieved.notes}")
        print(f"Timestamp: {retrieved.timestamp}")

        # 5. Validation Gate: Verify byte-for-byte integrity
        print("\n=== VALIDATION GATE: Integrity Check ===")
        new_hash = get_file_hash(artifact_path)
        print(f"Post-Annotation Artifact SHA-256: {new_hash}")

        assert original_hash == new_hash, "CRITICAL ERROR: Original artifact was mutated!"

        print("✅ SUCCESS: Original model evidence artifact is byte-for-byte unchanged.")
        print("✅ SUCCESS: Annotation is retrievable and correctly linked.")


if __name__ == "__main__":
    main()
