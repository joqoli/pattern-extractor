from __future__ import annotations

from typing import Any, Dict

from server.stages.base import BaseStage, StageInput, StageOutput


class IsolateSAMStage(BaseStage):
    name = "isolate_sam"
    cost_class = "cpu"
    expected_ms = 2000
    license_tag = "apache-2.0"

    def run(self, input_data: StageInput, cfg: Dict[str, Any]) -> StageOutput:
        image = input_data.image
        return StageOutput(
            image=image,
            metadata={"stage": "isolate_sam", "kind": "placeholder"},
            warnings=["SAM integration is scaffolded; model fallback is active."]
        )

