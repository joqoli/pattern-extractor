from __future__ import annotations

from typing import Dict, Any


def compute_metrics(tile: Any, source: Any, vector_data: Any | None = None) -> Dict[str, Any]:
    """Placeholder metric computation for the learning loop."""
    return {
        "seam_score": 0.08,
        "fidelity_lpips": 0.12,
        "vector_ssim": 0.90,
        "latency_ms": 800,
    }

