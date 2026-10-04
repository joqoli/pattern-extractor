from __future__ import annotations

from typing import Any, Dict

from server.stages.base import BaseStage, StageInput, StageOutput


class VTracerVectorizeStage(BaseStage):
    name = "vectorize_vtracer"
    cost_class = "cpu"
    expected_ms = 1200
    license_tag = "bsd-3-clause"

    def run(self, input_data: StageInput, cfg: Dict[str, Any]) -> StageOutput:
        return StageOutput(
            image=input_data.image,
            metadata={
                "stage": "vectorize_vtracer",
                "color_count": cfg.get("vector_color_count", 8),
                "simplify_tolerance": cfg.get("simplify_tolerance", 2.0),
            },
            warnings=[]
        )

