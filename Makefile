.PHONY: check lint type-check test

check: lint type-check test
	@echo "✅ All checks passed."

lint:
	@echo "Running ruff..."
	.venv/bin/ruff check src tests

type-check:
	@echo "Running mypy..."
	.venv/bin/mypy src tests

test:
	@echo "Running pytest..."
	.venv/bin/pytest tests/ -v --tb=short
