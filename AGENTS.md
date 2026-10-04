# AGENT TASKS

This repository is designed to be built by a coordinated team of AI agents. The work is split into reviewable phases, each with one owner and one definition of done.

## Team roles

- Architecture Lead: repo layout, architecture decisions, governance
- Backend Lead: API, pipeline orchestration, registry, caching
- CV Engineer: isolation, tiling, quality metrics, seam scoring
- ML Engineer: diffusion stages, warmup, benchmarking, model selection
- Frontend Engineer: web UI, preview, metrics dashboard
- DevOps: Docker, Compose, CI, regression gates
- Security/Compliance: license checks, secrets, validation

## Phase assignments

### Phase 1: Foundation
- Repo scaffold
- Docker and Makefile
- health endpoints
- test harness
- license docs

Owner: Architecture Lead + DevOps

### Phase 2: Core pipeline
- Stage interface
- SAM isolation stub
- classic tile stage
- VTracer vectorization stub
- export pipeline

Owner: Backend Lead + CV Engineer

### Phase 3: Quality path
- FabricDiffusion integration
- MaterialPalette integration
- seamless diffusion stages
- benchmark scoring

Owner: ML Engineer + CV Engineer

### Phase 4: Learning loop
- SQLite storage
- quality metrics
- feedback route
- selector bandit logic

Owner: Backend Lead + ML Engineer

### Phase 5: Performance engineering
- content cache
- async queue
- preview-first refinement
- budgets and CI gate

Owner: Backend Lead + DevOps

### Phase 6: Final release hardening
- docs
- security
- third-party inventory
- release notes

Owner: Security/Compliance + Architecture Lead

## Delivery rule

Every phase should produce a PR with tests, benchmark output when performance-relevant, and a changelog note.
