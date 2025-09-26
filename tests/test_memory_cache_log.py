import json
import time

import pytest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict


def load_chunk(name: str):
    path = Path("chunks") / f"{name}.py"
    spec = spec_from_file_location(f"voide_test_chunk_{name}", path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def make_container() -> Dict[str, Any]:
    return {"ops": {}, "tools": {}, "config": {}}


def register_chunk(name: str, container: Dict[str, Any]):
    module = load_chunk(name)
    module.build(container)
    return module



def test_memory_store(tmp_path, monkeypatch):
    storage_spec = spec_from_file_location(
        "voide.storage", Path("voide") / "storage.py"
    )
    storage_module = module_from_spec(storage_spec)
    assert storage_spec and storage_spec.loader
    storage_spec.loader.exec_module(storage_module)  # type: ignore[union-attr]
    MemoryStore = storage_module.MemoryStore

    db = str(tmp_path / "mem.db")
    ms = MemoryStore(db)
    ms.upsert("k1", {"val": 1})

    row = ms.get("k1")
    assert row["val"] == 1

    # advance time beyond TTL
    orig_time = storage_module.time.time
    monkeypatch.setattr(storage_module.time, "time", lambda: orig_time() + 10)
    assert ms.get("k1", ttl=1) is None



def test_cache_op(monkeypatch):
    container = make_container()
    mod = register_chunk("cache", container)
    mod._cache.clear()
    mod._timestamps.clear()
    container["ops"]["Child"] = lambda m, cfg, ct: {"x": time.time()}
    msg = {"prompt": "p"}
    cfg = {"strategy": "prefer", "ttl_seconds": 5, "child": "Child", "child_config": {}}
    op = container["ops"]["Cache"]
    out1 = op(msg, cfg, container)
    out2 = op(msg, cfg, container)
    assert out1 is out2
    orig_time = mod.time.time
    monkeypatch.setattr(mod.time, "time", lambda: orig_time() + 10)
    out3 = op(msg, cfg, container)
    assert out3 is not out2
    cfg["strategy"] = "refresh"
    out4 = op(msg, cfg, container)
    assert out4 is not out3


def test_memory_op_roundtrip():
    container = make_container()
    register_chunk("memory", container)
    op = container["ops"]["Memory"]
    message = {"id": "abc", "content": "alpha"}
    write_out = op(message, {"mode": "write", "key": "abc"}, container)
    assert write_out == {"stored": True, "key": "abc"}
    read_out = op({}, {"mode": "read", "query": "alpha", "k": 5}, container)
    assert any(item.get("content") == "alpha" for item in read_out["results"])

def test_json_log_append(tmp_path):
    from voide.storage import JSONLog

    log_path = tmp_path / "events.jsonl"
    log = JSONLog(log_path)
    log.append({"a": 1})
    log.append({"a": 2, "timestamp": "override"})

    contents = log_path.read_text(encoding="utf-8")
    assert contents.endswith("\n")

    lines = contents.splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])

    assert first["a"] == 1
    assert "timestamp" in first
    assert second["timestamp"] == "override"


def test_log_op(tmp_path):
    logf = tmp_path / "l.jsonl"
    container = make_container()
    register_chunk("log", container)

    op = container["ops"]["Log"]
    msg = {"a": 1}
    cfg = {"path": str(logf), "extra": {"b": 2}}
    out = op(msg, cfg, container)

    assert out == {"logged": True, "path": str(logf)}

    contents = logf.read_text(encoding="utf-8")
    assert contents.endswith("\n")

    lines = contents.splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["a"] == 1
    assert rec["b"] == 2
    assert rec["timestamp"].endswith("Z")
