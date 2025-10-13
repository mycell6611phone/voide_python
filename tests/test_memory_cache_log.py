import json

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



def test_cache_sliding_window_and_prepend_modes():
    container = make_container()
    mod = register_chunk("cache", container)
    mod._cache.clear()
    op = container["ops"]["Cache"]

    cfg = {"cache_id": "primary", "max_passes": 3, "prepend_mode": True}

    assert op({"stream_in": "A"}, cfg, container)["stream_out"] == ["A"]
    assert op({"stream_in": "B"}, cfg, container)["stream_out"] == ["A", "B"]
    assert op({"stream_in": "C"}, cfg, container)["stream_out"] == ["A", "B", "C"]
    assert op({"stream_in": "D"}, cfg, container)["stream_out"] == ["B", "C", "D"]

    cfg["prepend_mode"] = False
    assert op({"stream_in": "E"}, cfg, container)["stream_out"] == ["E", "D", "C"]


def test_cache_optional_input_toggle():
    container = make_container()
    mod = register_chunk("cache", container)
    mod._cache.clear()
    op = container["ops"]["Cache"]

    cfg_enabled = {
        "cache_id": "opt",
        "max_passes": 4,
        "enable_opt_in": True,
    }

    assert op({"opt_in": "X"}, cfg_enabled, container)["stream_out"] == ["X"]
    assert op({"stream_in": "A"}, cfg_enabled, container)["stream_out"] == ["X", "A"]

    cfg_disabled = {
        "cache_id": "opt_disabled",
        "max_passes": 4,
        "enable_opt_in": False,
    }

    assert op({"opt_in": "Y"}, cfg_disabled, container)["stream_out"] == []
    assert op({"stream_in": "B"}, cfg_disabled, container)["stream_out"] == ["B"]


def test_cache_token_limit_and_clear_after():
    container = make_container()
    mod = register_chunk("cache", container)
    mod._cache.clear()
    op = container["ops"]["Cache"]

    cfg = {
        "cache_id": "limit",
        "max_passes": 5,
        "token_limit": 3,
        "clear_after": 2,
    }

    assert op({"stream_in": "alpha beta"}, cfg, container)["stream_out"] == ["alpha beta"]
    # exceeds token budget, retains only most recent entry
    assert op({"stream_in": "gamma delta epsilon"}, cfg, container)["stream_out"] == [
        "gamma delta epsilon"
    ]

    # clear_after triggers before adding the next entry
    assert op({"stream_in": "zeta"}, cfg, container)["stream_out"] == ["zeta"]


def test_cache_clear_on_build_and_separate_keys():
    container = make_container()
    mod = register_chunk("cache", container)
    mod._cache.clear()
    op = container["ops"]["Cache"]

    cfg_a = {
        "cache_id": "primary",
        "max_passes": 3,
        "clear_on_build": True,
    }
    cfg_b = {"cache_id": "secondary", "max_passes": 2}

    assert op({"stream_in": "A"}, cfg_a, container)["stream_out"] == ["A"]
    assert op({"stream_in": "B"}, cfg_b, container)["stream_out"] == ["B"]

    # simulate workflow rebuild
    mod.build(container)
    assert op({}, cfg_a, container)["stream_out"] == []
    assert op({}, cfg_b, container)["stream_out"] == ["B"]


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
