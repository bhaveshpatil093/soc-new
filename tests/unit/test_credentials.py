"""
Test: No credential leakage (Constraint #4)

Verifies that:
1. No Python source file contains hardcoded credential-like strings.
2. Constants don't embed sensitive values.
3. Config files don't contain real credentials.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Patterns that suggest hardcoded credentials
# These are intentionally broad to catch potential leaks
CREDENTIAL_PATTERNS = [
    # password = "something" or password = 'something' (not empty, not placeholder)
    re.compile(
        r"""(?:password|passwd|secret|api_key|apikey|token|auth_token)\s*=\s*["'](?!your_|changeme|placeholder|CHANGE_ME|xxx|test_|mock_|fake_|dummy_)[^"']{3,}["']""",
        re.IGNORECASE,
    ),
    # Elasticsearch URLs with embedded credentials
    re.compile(r"https?://\w+:\w+@", re.IGNORECASE),
    # Base64-encoded auth headers that look real
    re.compile(r"Basic\s+(?!dGVzdDp0ZXN0)[A-Za-z0-9+/=]{20,}", re.IGNORECASE),
]

# Files/patterns that are allowed to have credential-like patterns
# (test files checking for credentials, .env.example with placeholders)
ALLOWED_FILES = {
    "test_credentials.py",  # This test file itself
    ".env.example",
    "conftest.py",
}


def _get_python_files(root: Path) -> list[Path]:
    """Get all Python files in the project source tree."""
    src_dir = root / "src"
    if not src_dir.exists():
        return []
    return list(src_dir.rglob("*.py"))


def _get_config_files(root: Path) -> list[Path]:
    """Get all YAML/JSON config files."""
    configs_dir = root / "configs"
    files: list[Path] = []
    if configs_dir.exists():
        files.extend(configs_dir.rglob("*.yaml"))
        files.extend(configs_dir.rglob("*.yml"))
        files.extend(configs_dir.rglob("*.json"))
    return files


class TestNoHardcodedCredentials:
    """Verify no source files contain hardcoded credentials."""

    def test_no_credentials_in_python_source(self, project_root: Path) -> None:
        """Scan all Python source files for credential-like patterns."""
        violations = []
        for py_file in _get_python_files(project_root):
            if py_file.name in ALLOWED_FILES:
                continue
            content = py_file.read_text()
            for pattern in CREDENTIAL_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(
                        f"{py_file.relative_to(project_root)}: {matches}"
                    )

        assert violations == [], (
            "Hardcoded credentials found (Constraint #4):\n"
            + "\n".join(violations)
        )

    def test_no_credentials_in_config_files(self, project_root: Path) -> None:
        """Scan all config files for credential-like patterns."""
        violations = []
        for config_file in _get_config_files(project_root):
            if config_file.name in ALLOWED_FILES:
                continue
            content = config_file.read_text()
            for pattern in CREDENTIAL_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    violations.append(
                        f"{config_file.relative_to(project_root)}: {matches}"
                    )

        assert violations == [], (
            "Hardcoded credentials in configs (Constraint #4):\n"
            + "\n".join(violations)
        )

    def test_constants_no_sensitive_values(self) -> None:
        """Verify constants module doesn't contain credential values."""
        from tads import constants

        # Check that no constant value looks like a real credential
        for name in dir(constants):
            if name.startswith("_"):
                continue
            value = getattr(constants, name)
            if isinstance(value, str):
                for pattern in CREDENTIAL_PATTERNS:
                    assert not pattern.search(f'x = "{value}"'), (
                        f"Constant {name} looks like a credential"
                    )


class TestCredentialEnvironmentLoading:
    """Verify credentials are designed to load from environment only."""

    def test_env_example_exists(self, project_root: Path) -> None:
        """An .env.example file must exist as a template."""
        env_example = project_root / ".env.example"
        assert env_example.exists(), ".env.example must exist"

    def test_env_example_has_required_vars(self, project_root: Path) -> None:
        """The .env.example file must demonstrate required authentication keys."""
        content = (project_root / ".env.example").read_text()
        assert "ELASTIC_HOST" in content
        assert "ELASTIC_USERNAME" in content
        assert "ELASTIC_PASSWORD" in content

    def test_env_example_has_no_real_values(self, project_root: Path) -> None:
        """The .env.example values must be placeholders, not real credentials."""
        content = (project_root / ".env.example").read_text()
        # Should contain placeholder text
        assert "your_" in content.lower() or "changeme" in content.lower() or "your-" in content.lower()

    def test_gitignore_excludes_env(self, project_root: Path) -> None:
        """.env must be in .gitignore."""
        gitignore = (project_root / ".gitignore").read_text()
        assert ".env" in gitignore
