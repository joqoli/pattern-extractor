from __future__ import annotations

from server.pipeline import PipelineConfig


def test_pipeline_config_defaults() -> None:
    config = PipelineConfig()
    assert config.preset == 'balanced'
    assert config.preview_mode is True

