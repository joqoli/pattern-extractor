from __future__ import annotations

from typing import Any, Dict, MutableMapping, Optional


class StageRegistry:
    """Simple plugin registry for stage implementations."""

    def __init__(self) -> None:
        self._registry: MutableMapping[str, Any] = {}

    def register(self, name: str, implementation: Any) -> None:
        self._registry[name] = implementation

    def get(self, name: str) -> Optional[Any]:
        return self._registry.get(name)

    def names(self) -> list[str]:
        return sorted(self._registry.keys())


registry = StageRegistry()


def register_default_stages() -> None:
    from server.stages.isolate_sam import IsolateSAMStage
    from server.stages.tile_classic import ClassicTileStage
    from server.stages.vectorize_vtracer import VTracerVectorizeStage

    registry.register("isolate_sam", IsolateSAMStage())
    registry.register("tile_classic", ClassicTileStage())
    registry.register("vectorize_vtracer", VTracerVectorizeStage())


register_default_stages()
