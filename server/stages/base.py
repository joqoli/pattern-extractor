from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class StageInput:
    image: Any
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StageOutput:
    image: Any
    metadata: Optional[Dict[str, Any]] = None
    warnings: List[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class BaseStage:
    """Base interface for all pipeline stages."""

    name: str = "base"
    cost_class: str = "cpu"
    expected_ms: int = 1000
    license_tag: str = "internal"

    def run(self, input_data: StageInput, cfg: Dict[str, Any]) -> StageOutput:
        raise NotImplementedError
