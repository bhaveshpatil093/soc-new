"""Tests for AnnotationStore."""

import tempfile
from pathlib import Path

from tads.investigation.annotations import AnnotationLabel, AnnotationStore


def test_annotation_store_append_and_retrieve() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "annotations.jsonl"
        store = AnnotationStore(storage_path=str(store_path))

        # Append 1
        store.append(
            target_id="EP-123",
            target_type="episode",
            label=AnnotationLabel.SECURITY_RELEVANT,
            analyst="alice",
            notes="Checked logs, definitely malicious.",
        )

        # Append 2
        store.append(
            target_id="EP-123",
            target_type="episode",
            label=AnnotationLabel.BENIGN,
            analyst="bob",
            notes="Wait no, this is just a vulnerability scanner.",
        )

        # Reload from disk to prove persistence
        new_store = AnnotationStore(storage_path=str(store_path))
        history = new_store.get_history("EP-123")

        assert len(history) == 2
        assert history[0].label == AnnotationLabel.SECURITY_RELEVANT
        assert history[1].label == AnnotationLabel.BENIGN
        assert history[1].analyst == "bob"
