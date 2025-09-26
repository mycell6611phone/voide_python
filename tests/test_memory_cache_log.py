import os
import time
import json
from pathlib import Path

def test_memory_store(tmp_path, monkeypatch):
    from voide.storage import MemoryStore
    db = str(tmp_path / "mem.db")
    ms = MemoryStore(db)
    ms.upsert("k1", {"val": 1})
    row = ms.get("k1")
    assert row["val"] == 1
    # advance time beyond TTL
    monkeypatch.setattr(time, "time", lambda: time.time() + 10)
    assert ms.get("k1", ttl=1) is None

def test_cache_op(tmp_path):
    from voide.chunks.cache import op_cache
    c = {"ops": {"Child": lambda m, cfg, ct: {"x": 1}}}
    msg = {"prompt": "p"}
    cfg = {"strategy": "prefer", "ttl_seconds": 5, "child": "Child", "child_config": {}}
    out1 = op_cache(msg, cfg, c)
    out2 = op_cache(msg, cfg, c)
    assert out1 is out2
    cfg["strategy"] = "refresh"
    out3 = op_cache(msg, cfg, c)
    assert out3 is not out2

def test_log_op(tmp_path):
    from voide.chunks.log import op_log
    logf = tmp_path / "l.jsonl"
    msg = {"a": 1}
    cfg = {"path": str(logf)}
    out = op_log(msg, cfg, {})
    assert out.get("logged")
    lines = logf.read_text().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["a"] == 1 and "timestamp" in rec

