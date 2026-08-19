from pathlib import Path

import pytest
import yaml

from tads.schema.mapping import SchemaInspector


@pytest.fixture
def mock_config_path(tmp_path: Path) -> Path:
    config = {
        "canonical_fields": {
            "timestamp": {"candidates": ["@timestamp", "time"]},
            "user_name": {"candidates": ["user.name", "username"]},
            "source_ip": {"candidates": ["source.ip", "src_ip"]}
        }
    }
    config_file = tmp_path / "field_mapping.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return config_file

class TestSchemaInspector:

    def test_loads_config_successfully(self, mock_config_path: Path) -> None:
        inspector = SchemaInspector(mapping_file_path=mock_config_path)
        assert "timestamp" in inspector.canonical_definitions
        assert "user_name" in inspector.canonical_definitions

    def test_inspect_and_map_exact_matches(self, mock_config_path: Path) -> None:
        inspector = SchemaInspector(mapping_file_path=mock_config_path)
        discovered = ["@timestamp", "user.name", "source.ip"]

        report = inspector.inspect_and_map(discovered)
        assert report.mapped_fields["@timestamp"] == "timestamp"
        assert report.mapped_fields["user.name"] == "user_name"
        assert report.mapped_fields["source.ip"] == "source_ip"

        assert len(report.unmapped_fields) == 0
        assert len(report.missing_canonical_fields) == 0
        assert report.coverage_percentage == 100.0

    def test_inspect_and_map_fallback_candidates(self, mock_config_path: Path) -> None:
        inspector = SchemaInspector(mapping_file_path=mock_config_path)
        discovered = ["time", "username", "src_ip"]

        report = inspector.inspect_and_map(discovered)
        assert report.mapped_fields["time"] == "timestamp"
        assert report.mapped_fields["username"] == "user_name"
        assert report.mapped_fields["src_ip"] == "source_ip"

        assert len(report.missing_canonical_fields) == 0

    def test_inspect_and_map_partial_coverage_with_unknown_fields(self, mock_config_path: Path) -> None:
        inspector = SchemaInspector(mapping_file_path=mock_config_path)
        discovered = ["@timestamp", "random_id", "unknown_metric"]

        report = inspector.inspect_and_map(discovered)
        assert report.mapped_fields["@timestamp"] == "timestamp"

        assert "random_id" in report.unmapped_fields
        assert "unknown_metric" in report.unmapped_fields
        assert len(report.unmapped_fields) == 2

        assert "user_name" in report.missing_canonical_fields
        assert "source_ip" in report.missing_canonical_fields

        # 1 out of 3 canonical fields found
        assert pytest.approx(report.coverage_percentage) == 33.33333333333333

    def test_inspect_and_map_candidate_priority(self, mock_config_path: Path) -> None:
        inspector = SchemaInspector(mapping_file_path=mock_config_path)
        # Both "@timestamp" and "time" are discovered, it should map "@timestamp" because it's first
        discovered = ["@timestamp", "time"]

        report = inspector.inspect_and_map(discovered)
        assert report.mapped_fields["@timestamp"] == "timestamp"
        # "time" should fall into unmapped because the canonical field is already satisfied by @timestamp!
        # Actually, wait! The way we implemented it:
        # Check candidates in order of preference. If found, map it and break.
        # So "time" never gets mapped, it gets treated as unmapped.
        assert "time" in report.unmapped_fields
