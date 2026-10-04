from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Pattern Extractor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "pattern-extractor"}


@app.get("/metrics")
def metrics() -> Dict[str, Any]:
    return {
        "pipeline": {"status": "scaffolded"},
        "latency_ms": {"p50": 0, "p95": 0},
        "quality": {"seam_score": 0.0},
    }


@app.post("/extract")
def extract() -> Dict[str, Any]:
    return {
        "status": "accepted",
        "message": "Pipeline scaffold is active.",
        "formats": ["svg", "eps", "ai"],
    }


@app.post("/feedback")
def feedback() -> Dict[str, Any]:
    return {"status": "accepted", "message": "Feedback logging is scaffolded."}
