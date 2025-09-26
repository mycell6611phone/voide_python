# File: workspace/chunks/memory.py
"""Memory op: read/write to MemoryStore."""
from __future__ import annotations
from typing import Any, Dict
import time
from voide.storage import MemoryStore


provides = ["ops", "memory"]
requires = []


def op_memory(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
    mode = config.get("mode", "read")
    store: MemoryStore = container.get("memory")
    if store is None:
        store = MemoryStore()
        container["memory"] = store
    if mode == "write":
        key = config.get("key", message.get("id", str(time.time())))
        store.upsert(key, message)
        return {"stored": True, "key": key}
    # read
    query = config.get("query", "")
    k = int(config.get("k", 8))
    results = store.query(query, k)
    return {"results": results}


def build(container: Dict[str, Any]) -> None:
    container.setdefault("ops", {})["Memory"] = op_memory
    if "memory" not in container:
        container["memory"] = MemoryStore()
