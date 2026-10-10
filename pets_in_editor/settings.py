"""Persistent settings for Pets in Editor."""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "settings.json"

DEFAULTS = {
    "enabled": True,
    "selected": "",
    "scale": 0.55,
    "speed": 65,
}


def _validated(obj):
    result = DEFAULTS.copy()
    if not isinstance(obj, dict):
        return result

    if isinstance(obj.get("enabled"), bool):
        result["enabled"] = obj["enabled"]
    if isinstance(obj.get("selected"), str):
        result["selected"] = obj["selected"]

    try:
        result["scale"] = min(2.0, max(0.2, float(obj.get("scale", result["scale"]))))
    except (TypeError, ValueError):
        pass

    try:
        result["speed"] = min(400, max(0, int(obj.get("speed", result["speed"]))))
    except (TypeError, ValueError):
        pass

    return result


def load():
    try:
        return _validated(json.loads(PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return DEFAULTS.copy()


def save(settings):
    values = _validated(settings)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(values, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(PATH)
