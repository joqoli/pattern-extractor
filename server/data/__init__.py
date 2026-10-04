from __future__ import annotations

from pathlib import Path
import json
from typing import Any


__all__ = ["DATASET_MANIFEST_PATH"]

DATASET_MANIFEST_PATH = Path(__file__).with_name("dataset_manifest.json")


def load_manifest() -> dict[str, Any]:
    with DATASET_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
