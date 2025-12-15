from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlencode


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_query_string(params: dict[str, str | int | float | bool | None]) -> str:
    items: list[tuple[str, str]] = []
    for key in sorted(params.keys()):
        raw_value = params[key]
        if raw_value is None:
            continue
        items.append((key, str(raw_value)))
    return urlencode(items)


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8"))
