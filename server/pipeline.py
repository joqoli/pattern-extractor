from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PipelineConfig:
    """Config keyed by stage name with preset defaults."""

    preset: str = "balanced"
    stage_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quality_mode: bool = False
    preview_mode: bool = True
    crop: Optional[Dict[str, Any]] = None

    def get_stage_config(self, stage_name: str) -> Dict[str, Any]:
        return self.stage_configs.get(stage_name, {})

