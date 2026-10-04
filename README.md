# Pattern Extractor Suite

This repository provides a local-first garment pattern extraction system with a CPU-safe baseline pipeline, vector export support, and a dataset acquisition workflow for embroidery, textile, and fashion sources.

## Quick start

```bash
make dev
```

Then open the local UI at http://localhost:8000.

## Dataset acquisition

The project includes a dataset workspace + automated preparation script for the sources described in `docs/DATASETS.md`.

```bash
make datasets
```

This creates the dataset directory layout and writes a manual download guide for each source. Some datasets require license review or manual downloads due to access restrictions.

## Docker volume strategy

The repo mounts a persistent dataset volume at `/datasets` in the backend container so benchmark, source, and training artifacts do not live in the application image.

```bash
docker compose up --build
```

The compose file exposes the workspace as a named volume mapped to `./datasets` on the host.
