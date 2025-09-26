"""JSONL logging chunk."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from voide.storage import JSONLog


provides = ["ops"]
requires: list[str] = []

_LOGGER_CACHE_KEY = "logs"


def _get_logger(path: Path, container: Dict[str, Any]) -> JSONLog:
    """Return a cached ``JSONLog`` instance for *path* within *container*."""

    cache = container.setdefault(_LOGGER_CACHE_KEY, {})
    key = str(path)
    logger = cache.get(key)
    if not isinstance(logger, JSONLog):
        logger = JSONLog(path)
        cache[key] = logger
    return logger


def op_log(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
    """Append *message* to the configured JSONL log file."""

    if not isinstance(message, dict):
        raise TypeError("log op expects message dict")

    path_value = config.get("path")
    if not path_value:
        raise ValueError("log op requires 'path' in config")

    path = Path(path_value).expanduser()
    extra = config.get("extra") or {}
    if not isinstance(extra, dict):
        raise TypeError("log op expects config['extra'] to be a dict if provided")

    record: Dict[str, Any] = {**extra, **message}
    record.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    # Ensure the payload is JSON serialisable before writing.
    json.dumps(record, ensure_ascii=False)

    logger = _get_logger(path, container)
    logger.append(record)

    return {"logged": True, "path": str(path)}


def build(container: Dict[str, Any]) -> None:
    """Register the Log op within *container*."""

    container.setdefault("ops", {})["Log"] = op_log
