# Makefile

.PHONY: dev test bench lint clean datasets download-datasets

PYTHON ?= python3
PIP ?= pip

help:
	@echo "Available targets: dev, test, bench, datasets, lint, clean"

dev:
	@echo "Starting local developer environment..."
	@docker compose up --build

datasets:
	@$(PYTHON) server/data/download_datasets.py --output-root ./datasets

download-datasets: datasets

test:
	@pytest -q

bench:
	@mkdir -p bench/results
	@$(PYTHON) - <<'PY'
import json, os
path = 'bench/results/latest.json'
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump({"status": "not-run", "note": "benchmark suite scaffolded"}, f, indent=2)
print('Bench scaffold written to', path)
PY

lint:
	@echo "Lint scaffold is installed in CI; this phase is intentionally minimal at startup."

clean:
	@rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	@find . -type d -name '__pycache__' -exec rm -rf {} +
