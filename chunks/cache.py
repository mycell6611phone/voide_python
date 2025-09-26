# File: workspace/chunks/cache.py
"""Cache op: wraps downstream op with TTL cache."""
from __future__ import annotations
import hashlib
import time
from typing import Any, Dict


provides = ["ops"]
requires = []


_cache: Dict[str, Any] = {}
_timestamps: Dict[str, float] = {}


def op_cache(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
strategy = config.get("strategy", "off")
ttl = float(config.get("ttl_seconds", 0))
base = message.get("prompt") or str(message.get("messages", ""))
h = hashlib.sha256(base.encode()).hexdigest()
now = time.time()
if strategy == "prefer":
if h in _cache and now - _timestamps.get(h, 0) <= ttl:
return _cache[h]
res = _call_child(message, config, container)
_cache[h] = res
_timestamps[h] = now
return res
if strategy == "refresh":
res = _call_child(message, config, container)
_cache[h] = res
_timestamps[h] = now
return res
# off
return _call_child(message, config, container)


def _call_child(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
child = config.get("child")
if not child:
raise RuntimeError("cache child op not specified in config['child']")
op = container.get("ops", {}).get(child)
if not callable(op):
raise RuntimeError(f"Unknown child op: {child}")
return op(message, config.get("child_config", {}), container)


def build(container: Dict[str, Any]) -> None:
container.setdefault("ops", {})["Cache"] = op_cache
