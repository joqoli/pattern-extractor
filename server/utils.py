from __future__ import annotations

import hashlib


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
