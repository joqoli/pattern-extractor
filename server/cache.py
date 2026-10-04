from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


class ContentAddressedCache:
    """Simple in-memory cache keyed by hash(image bytes + crop + config)."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def _make_key(self, image_bytes: bytes, crop: Optional[Dict[str, Any]], config: Dict[str, Any]) -> str:
        payload = {
            "image": hashlib.sha256(image_bytes).hexdigest(),
            "crop": crop or {},
            "config": config,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def get(self, image_bytes: bytes, crop: Optional[Dict[str, Any]], config: Dict[str, Any]) -> Any:
        return self._store.get(self._make_key(image_bytes, crop, config))

    def set(self, image_bytes: bytes, crop: Optional[Dict[str, Any]], config: Dict[str, Any], value: Any) -> None:
        key = self._make_key(image_bytes, crop, config)
        self._store[key] = value


cache = ContentAddressedCache()
