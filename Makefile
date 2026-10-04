.PHONY: dev test bench lint clean datasets download-datasets

PYTHON ?= python3
PIP ?= pip

help:
	@echo "Available targets:"
	@echo "  dev                  - Start dev environment (Docker)"
	@echo "  download-datasets    - Download all enabled datasets"
	@echo "  validate-datasets    - Validate downloaded datasets"
	@echo "  test                 - Run tests"
	@echo "  bench                - Run benchmarks"
	@echo "  lint                 - Run linters"
	@echo "  clean                - Clean build artifacts"

.PHONY: dev
dev:
	@echo "Starting local developer environment..."
	@docker compose up --build

.PHONY: download-datasets
download-datasets:
	@echo "Downloading datasets (this may take a while)..."
	@$(PYTHON) server/data/fetcher.py --output-root ./datasets

.PHONY: download-datasets-category
download-datasets-category:
	@echo "Usage: make download-datasets-category CATEGORY=embroidery"
	@$(PYTHON) server/data/fetcher.py --output-root ./datasets --category $(CATEGORY)

.PHONY: download-datasets-single
download-datasets-single:
	@echo "Usage: make download-datasets-single NAME=dtd-texture"
	@$(PYTHON) server/data/fetcher.py --output-root ./datasets --name $(NAME)

.PHONY: download-datasets-dry-run
download-datasets-dry-run:
	@echo "Dry run: showing what would be downloaded..."
	@$(PYTHON) server/data/fetcher.py --output-root ./datasets --dry-run

.PHONY: validate-datasets
validate-datasets:
	@$(PYTHON) server/data/validate_datasets.py ./datasets

.PHONY: datasets
datasets: download-datasets

.PHONY: test
test:
	@pytest -q

.PHONY: bench
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

.PHONY: lint
lint:
	@echo "Lint scaffold installed; running in CI."

.PHONY: clean
clean:
	@rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"
