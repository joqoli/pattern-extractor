from __future__ import annotations

from typing import Any, Dict, List


class Selector:
    """Simple config selector that prefers lower latency and higher quality."""

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def choose(self, image_features: Dict[str, Any], options: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not options:
            raise ValueError("No selector options provided.")
        ranked = sorted(options, key=lambda cfg: (cfg.get("latency_ms", 99999), -cfg.get("quality_score", 0)))
        choice = ranked[0]
        self.history.append({"image_features": image_features, "choice": choice})
        return choice

