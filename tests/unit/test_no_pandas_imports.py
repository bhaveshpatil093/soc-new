"""
Test: No unqualified pandas imports (Constraint #17)

AST-scans all Python source files to flag pandas usage.
Polars, PyArrow, and DuckDB are the approved data processing tools.

Pandas is allowed ONLY if the import line contains a comment
with "# pandas-justified:" explaining why it's needed.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _get_all_python_files(root: Path) -> list[Path]:
    """Get all Python files under src/."""
    src_dir = root / "src"
    if not src_dir.exists():
        return []
    return list(src_dir.rglob("*.py"))


def _check_file_for_pandas_usage(filepath: Path) -> list[str]:
    """
    Parse a Python file's AST and check for pandas imports.

    Returns a list of violation descriptions.
    Pandas is allowed only if the source line contains '# pandas-justified:'.
    """
    violations = []
    try:
        source = filepath.read_text()
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [f"SyntaxError in {filepath}"]

    for node in ast.walk(tree):
        is_pandas_import = False

        # Check: import pandas / import pandas as pd
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pandas" or alias.name.startswith("pandas."):
                    is_pandas_import = True

        # Check: from pandas import ... / from pandas.xxx import ...
        elif isinstance(node, ast.ImportFrom) and node.module and (
            node.module == "pandas" or node.module.startswith("pandas.")
        ):
            is_pandas_import = True

        if is_pandas_import:
            # Check if the line has a justification comment
            node_lineno = getattr(node, "lineno", 0)
            line_idx = node_lineno - 1
            if line_idx >= 0 and line_idx < len(lines):
                line_content = lines[line_idx]
                if "# pandas-justified:" not in line_content:
                    violations.append(
                        f"Line {node_lineno}: pandas import without justification — "
                        f"Use Polars/PyArrow/DuckDB instead (Constraint #17). "
                        f"If pandas is truly needed, add '# pandas-justified: <reason>'"
                    )

    return violations


class TestNoPandasImports:
    """Verify no unjustified pandas imports in source code."""

    def test_no_pandas_in_source(self, project_root: Path) -> None:
        """Scan all Python source files for unjustified pandas imports."""
        all_violations: dict[str, list[str]] = {}

        for py_file in _get_all_python_files(project_root):
            violations = _check_file_for_pandas_usage(py_file)
            if violations:
                rel_path = str(py_file.relative_to(project_root))
                all_violations[rel_path] = violations

        if all_violations:
            msg_lines = [
                "Unjustified pandas imports found (Constraint #17):",
                "Use Polars, PyArrow, or DuckDB instead.",
            ]
            for filepath, violations in all_violations.items():
                msg_lines.append(f"\n  {filepath}:")
                for v in violations:
                    msg_lines.append(f"    - {v}")
            raise AssertionError("\n".join(msg_lines))
