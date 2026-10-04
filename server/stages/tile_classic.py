from __future__ import annotations

from typing import Any, Dict

from server.stages.base import BaseStage, StageInput, StageOutput


class ClassicTileStage(BaseStage):
    name = "tile_classic"
    cost_class = "cpu"
    expected_ms = 400
    license_tag = "internal"

    def run(self, input_data: StageInput, cfg: Dict[str, Any]) -> StageOutput:
        tile = input_data.image
        return StageOutput(
            image=tile,
            metadata={"stage": "tile_classic", "type": "blend-based", "tile_size": cfg.get("tile_size", 512)},
            warnings=[]
        )

