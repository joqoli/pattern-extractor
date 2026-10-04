# Pattern Extractor Suite

This repository is the starter implementation for a local-first garment pattern extraction suite.

## Quick start

```bash
make dev
```

Then open the UI at http://localhost:8000 or use the API directly at http://localhost:8000/health.

## Architecture

- `web/` front-end shell
- `server/` FastAPI backend and pipeline stages
- `tests/` validation suite
- `docs/` design notes and roadmap
- `bench/` benchmarking, budgets, fixtures

## Scope

The project follows the design in `docs/PLAN.md` and supports a CPU-safe baseline pipeline:

1. isolate garment
2. flatten / normalize
3. tile seamless pattern
4. vectorize output
5. save SVG/EPS/AI exports

The code here is intentionally structured for incremental completion by multiple AI agent tasks.
