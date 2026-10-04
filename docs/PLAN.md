# Pattern Extractor Project Plan

This document is the working plan for the `pattern-extractor` repository. It is intentionally written as a concrete engineering blueprint for a multi-agent implementation.

## 1. Repo structure

```text
pattern-extractor/
├── web/
│   ├── index.html
│   ├── src/
│   └── styles/
├── server/
│   ├── api.py
│   ├── pipeline.py
│   ├── registry.py
│   ├── cache.py
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── isolate_sam.py
│   │   ├── tile_classic.py
│   │   ├── vectorize_vtracer.py
│   │   └── ...
│   └── learning/
│       ├── __init__.py
│       ├── store.py
│       ├── metrics.py
│       └── selector.py
├── docs/
│   ├── PLAN.md
│   ├── INTEGRATION_NOTES.md
│   └── ARCHITECTURE.md
├── bench/
│   ├── budgets.json
│   ├── fixtures/
│   └── results/
├── tests/
│   ├── test_api.py
│   ├── test_pipeline.py
│   └── ...
├── .github/workflows/
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── THIRD_PARTY.md
├── AGENTS.md
├── LICENSE
└── README.md
```

## 2. Implementation phases

### Phase 1: repo scaffold and dev environment
- Create repo layout
- Add health endpoints and basic UI shell
- Add Docker + Makefile
- Add CI skeleton
- Add license and integration notes placeholders

### Phase 2: core CPU-safe pipeline
- Stage interface + registry
- SAM isolation stub
- Classic tile generation
- Vectorization stub
- Export format scaffolding

### Phase 3: optional diffusion quality stages
- FabricDiffusion integration
- MaterialPalette integration
- Seamless diffusion tile stages
- Benchmarking and quality gates

### Phase 4: learning loop
- SQLite logging
- metrics collection
- feedback-based selection
- contextual bandit logic

### Phase 5: performance budgets and CI regression gates
- cache layer
- async processing queue
- preview-first refinement
- p50 latency regression checks

### Phase 6: hardening and documentation
- docs cleanup
- security review
- license verification
- release notes

## 3. Safety rules

- Do not claim autonomous model mutation; learning is feedback-driven only.
- Do not rely on unlicensed models or packages by default; document them and gate optional use.
- Keep the CPU fallback always functional.
- Benchmark and CI must govern performance claims.

## 4. Immediate goals for this repo state

We are starting from an empty repo scaffold and will implement the foundation first. The first pass focuses on correctness and reviewability rather than full model inference.

## 5. Multi-agent task assignments

See `AGENTS.md` for the detailed task schedule and owner mapping.
