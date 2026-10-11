"""Persistent settings for Pets in Editor."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

PATH = Path(__file__).resolve().parent / "settings.json"
logger = logging.getLogger(__name__)

ACTIVITY_LEVELS = ("lazy", "normal", "energetic")

DEFAULTS = {
    "enabled": True,
    "selected": "",
    "scale": 0.55,
    "speed": 65,
    "activity_level": "normal",
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
        scale = float(obj.get("scale", result["scale"]))
        if math.isfinite(scale):
            result["scale"] = min(2.0, max(0.2, scale))
    except (TypeError, ValueError, OverflowError):
        pass

    try:
        result["speed"] = min(400, max(0, int(obj.get("speed", result["speed"]))))
    except (TypeError, ValueError, OverflowError):
        pass

    activity_level = obj.get("activity_level")
    if isinstance(activity_level, str) and activity_level.lower() in ACTIVITY_LEVELS:
        result["activity_level"] = activity_level.lower()

    return result


def load():
    try:
        return _validated(json.loads(PATH.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return DEFAULTS.copy()
    except (OSError, ValueError, TypeError):
        logger.exception("Unable to read pet settings from %s", PATH)
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
