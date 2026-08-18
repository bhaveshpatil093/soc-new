"""
Test: Project independence verification

Verifies that this project has:
- Zero import paths into any external project
- Zero config references to any external project
- Zero file-system references into any external project directory
- No submodule, symlink, or shared package relationships

This project (TADS / soc-new) must be completely self-contained.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Patterns that would indicate dependency on an external project
# These are checked against all source and config files
EXTERNAL_PROJECT_PATTERNS = [
    # Import from external SOC project packages
    re.compile(r"\bfrom\s+soc\b", re.IGNORECASE),
    re.compile(r"\bimport\s+soc\b", re.IGNORECASE),
    re.compile(r"\bfrom\s+soc_dashboard\b", re.IGNORECASE),
    re.compile(r"\bimport\s+soc_dashboard\b", re.IGNORECASE),
    # File-system references to external project directories
    re.compile(r"soc-dashboard", re.IGNORECASE),
    re.compile(r"soc_dashboard", re.IGNORECASE),
]

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini", ".md"}

# Files that are allowed to mention external projects (like this test itself)
ALLOWED_FILES = {
    "test_independence.py",
    "implementation_plan.md",
}


def _get_scannable_files(root: Path) -> list[Path]:
    """Get all files that should be scanned for external references."""
    files = []
    for ext in SCAN_EXTENSIONS:
        files.extend(root.rglob(f"*{ext}"))
    # Exclude .git directory and virtual environments
    files = [
        f for f in files
        if ".git" not in f.parts
        and ".venv" not in f.parts
        and "venv" not in f.parts
        and "__pycache__" not in f.parts
    ]
    return files


class TestProjectIndependence:
    """Verify complete independence from external projects."""

    def test_no_external_imports_in_source(self, project_root: Path) -> None:
        """No Python source file imports from external project packages."""
        violations = []
        src_dir = project_root / "src"
        if not src_dir.exists():
            return

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            for pattern in EXTERNAL_PROJECT_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(
                        f"{py_file.relative_to(project_root)}: {matches}"
                    )

        assert violations == [], (
            f"External project references in source:\n" + "\n".join(violations)
        )

    def test_no_external_references_in_configs(self, project_root: Path) -> None:
        """No config file references external project paths or packages."""
        violations = []
        configs_dir = project_root / "configs"
        if not configs_dir.exists():
            return

        for config_file in configs_dir.rglob("*"):
            if config_file.suffix not in SCAN_EXTENSIONS:
                continue
            content = config_file.read_text()
            for pattern in EXTERNAL_PROJECT_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(
                        f"{config_file.relative_to(project_root)}: {matches}"
                    )

        assert violations == [], (
            f"External project references in configs:\n" + "\n".join(violations)
        )

    def test_no_symlinks_to_external(self, project_root: Path) -> None:
        """No symlinks point outside the project directory."""
        # Directories that are expected to have external symlinks
        excluded_dirs = {".venv", "venv", ".git", "__pycache__", "node_modules"}
        violations = []
        for path in project_root.rglob("*"):
            # Skip paths inside excluded directories
            if any(part in excluded_dirs for part in path.parts):
                continue
            if path.is_symlink():
                target = path.resolve()
                if not str(target).startswith(str(project_root)):
                    violations.append(f"{path} -> {target}")

        assert violations == [], (
            f"Symlinks to external directories:\n" + "\n".join(violations)
        )

    def test_no_git_submodules(self, project_root: Path) -> None:
        """No .gitmodules file exists (no submodule dependencies)."""
        gitmodules = project_root / ".gitmodules"
        assert not gitmodules.exists(), (
            "Project must not use git submodules for external project dependencies"
        )

    def test_own_pyproject_toml(self, project_root: Path) -> None:
        """Project has its own pyproject.toml (independent package management)."""
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists(), "Project must have its own pyproject.toml"

        content = pyproject.read_text()
        # Verify the project name is 'tads', not an external project
        assert 'name = "tads"' in content, (
            "pyproject.toml must define this project as 'tads'"
        )

    def test_no_external_path_in_pyproject(self, project_root: Path) -> None:
        """pyproject.toml doesn't reference external project paths."""
        content = (project_root / "pyproject.toml").read_text()
        for pattern in EXTERNAL_PROJECT_PATTERNS:
            matches = pattern.findall(content)
            assert matches == [], (
                f"External references in pyproject.toml: {matches}"
            )
