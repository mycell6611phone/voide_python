from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog
from typing import Dict, Any

def prompt_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    template = simpledialog.askstring("Prompt Options", "Template (use {task}):", initialvalue=cfg.get("template", "{task}"), parent=master)
    if template is None:
        return cfg
    cfg["template"] = template
    return cfg

def llm_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    backend = simpledialog.askstring("LLM Options", "Backend (echo|openai|llama_cpp):", initialvalue=cfg.get("backend", "echo"), parent=master)
    if backend is not None:
        cfg["backend"] = backend
    model = simpledialog.askstring("LLM Options", "OpenAI model:", initialvalue=cfg.get("model", "gpt-4o-mini"), parent=master)
    if model is not None:
        cfg["model"] = model
    model_path = simpledialog.askstring("LLM Options", "llama.cpp model_path:", initialvalue=cfg.get("model_path", ""), parent=master)
    if model_path is not None:
        cfg["model_path"] = model_path
    fwd = simpledialog.askstring("LLM Options", "Forward input with response? (y/n):", initialvalue="y" if cfg.get("forward_input_with_response", False) else "n", parent=master)
    if fwd is not None:
        cfg["forward_input_with_response"] = fwd.lower().startswith("y")
    return cfg

def memory_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    mode = simpledialog.askstring("Memory Options", "Mode (read|write):", initialvalue=cfg.get("mode", "read"), parent=master)
    if mode is not None:
        cfg["mode"] = mode
    query = simpledialog.askstring("Memory Options", "Query (for read):", initialvalue=cfg.get("query", ""), parent=master)
    if query is not None:
        cfg["query"] = query
    k = simpledialog.askinteger("Memory Options", "k (for read):", initialvalue=int(cfg.get("k", 8)), parent=master, minvalue=1)
    if k is not None:
        cfg["k"] = int(k)
    return cfg

def cache_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    strategy = simpledialog.askstring("Cache Options", "Strategy (off|prefer|refresh):", initialvalue=cfg.get("strategy", "prefer"), parent=master)
    if strategy is not None:
        cfg["strategy"] = strategy
    ttl = simpledialog.askinteger("Cache Options", "TTL seconds:", initialvalue=int(cfg.get("ttl_seconds", 300)), parent=master, minvalue=0)
    if ttl is not None:
        cfg["ttl_seconds"] = int(ttl)
    return cfg

def log_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    path = simpledialog.askstring("Log Options", "Path to JSONL:", initialvalue=cfg.get("path", "artifacts/run.log"), parent=master)
    if path is not None:
        cfg["path"] = path
    return cfg

def divider_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    route_key = simpledialog.askstring("Divider Options", "Route key:", initialvalue=cfg.get("route_key", "route"), parent=master)
    if route_key is not None:
        cfg["route_key"] = route_key
    mapping_str = simpledialog.askstring("Divider Options", "Mapping (value:port,comma-separated):", initialvalue=cfg.get("_mapping_str", "alpha:A,beta:B"), parent=master)
    if mapping_str is not None:
        m: Dict[str, str] = {}
        for part in mapping_str.split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                m[k.strip()] = v.strip()
        cfg["mapping"] = m
        cfg["_mapping_str"] = mapping_str
    return cfg

def toolcall_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    tool = simpledialog.askstring("ToolCall Options", "Tool name:", initialvalue=cfg.get("tool", "python_eval"), parent=master)
    if tool is not None:
        cfg["tool"] = tool
    expr = simpledialog.askstring("ToolCall Options", "python_eval expr:", initialvalue=cfg.get("expr", "2+2"), parent=master)
    if expr is not None:
        cfg["args"] = {"expr": expr}
        cfg["expr"] = expr
    return cfg

def debate_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    rounds = simpledialog.askinteger("Debate/Loop Options", "Rounds:", initialvalue=int(cfg.get("rounds", 2)), parent=master, minvalue=1)
    if rounds is not None:
        cfg["rounds"] = int(rounds)
    return cfg
