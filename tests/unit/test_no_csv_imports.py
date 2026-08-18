"""
Test: No CSV imports (Constraint #16)

AST-scans all Python source files to ensure no code imports or uses
the `csv` module. All data must use Parquet format.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _get_all_python_files(root: Path) -> list[Path]:
    """Get all Python files under src/."""
    src_dir = root / "src"
    if not src_dir.exists():
        return []
    return list(src_dir.rglob("*.py"))


def _check_file_for_csv_usage(filepath: Path) -> list[str]:
    """
    Parse a Python file's AST and check for csv module usage.

    Returns a list of violation descriptions.
    """
    violations = []
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [f"SyntaxError in {filepath}"]

    for node in ast.walk(tree):
        # Check: import csv
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "csv" or alias.name.startswith("csv."):
                    violations.append(
                        f"Line {node.lineno}: 'import {alias.name}' — "
                        f"CSV imports forbidden (Constraint #16)"
                    )

        # Check: from csv import ...
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "csv" or node.module.startswith("csv.")):
                names = ", ".join(a.name for a in node.names)
                violations.append(
                    f"Line {node.lineno}: 'from {node.module} import {names}' — "
                    f"CSV imports forbidden (Constraint #16)"
                )

    return violations


class TestNoCSVImports:
    """Verify no source file imports the csv module."""

    def test_no_csv_in_source(self, project_root: Path) -> None:
        """Scan all Python source files for csv imports."""
        all_violations: dict[str, list[str]] = {}

        for py_file in _get_all_python_files(project_root):
            violations = _check_file_for_csv_usage(py_file)
            if violations:
                rel_path = str(py_file.relative_to(project_root))
                all_violations[rel_path] = violations

        if all_violations:
            msg_lines = ["CSV imports found in source (Constraint #16):"]
            for filepath, violations in all_violations.items():
                msg_lines.append(f"\n  {filepath}:")
                for v in violations:
                    msg_lines.append(f"    - {v}")
            raise AssertionError("\n".join(msg_lines))

    def test_no_csv_files_in_project(self, project_root: Path) -> None:
        """Verify no .csv files exist in the project (except test fixtures and venvs)."""
        excluded_dirs = {".venv", "venv", ".git", "__pycache__", "node_modules"}
        csv_files = [
            f for f in project_root.rglob("*.csv")
            if not any(part in excluded_dirs for part in f.parts)
        ]
        # Filter out any files in test directories that might use CSV for fixture comparison
        non_test_csv = [f for f in csv_files if "test" not in str(f).lower()]
        assert non_test_csv == [], (
            f"CSV files found in project (Constraint #16): {non_test_csv}"
        )
