"""Sliding window cache chunk supporting dual-input aggregation."""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict


provides = ["ops"]
requires: list[str] = []


@dataclass
class CacheEntry:
    payload: Any
    tokens: int
    source: str


@dataclass
class CacheState:
    history: Deque[CacheEntry] = field(default_factory=deque)
    passes_since_clear: int = 0
    total_tokens: int = 0
    generation: int = -1

    def clear(self) -> None:
        self.history.clear()
        self.passes_since_clear = 0
        self.total_tokens = 0


_cache: Dict[str, CacheState] = {}
_build_generation: int = 0


def _normalize_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < minimum:
        return minimum
    return parsed


def _token_count(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, bool):
        return 1
    if isinstance(payload, (int, float)):
        return 1
    if isinstance(payload, str):
        text = payload.strip()
        return 0 if not text else len(text.split())
    if isinstance(payload, dict):
        return sum(_token_count(v) for v in payload.values())
    if isinstance(payload, (list, tuple, set)):
        return sum(_token_count(v) for v in payload)
    text = str(payload).strip()
    return 0 if not text else len(text.split())


def _trim_history(state: CacheState, max_passes: int, token_limit: int) -> None:
    while len(state.history) > max_passes:
        removed = state.history.popleft()
        state.total_tokens -= removed.tokens
    if token_limit > 0:
        while state.total_tokens > token_limit and len(state.history) > 1:
            removed = state.history.popleft()
            state.total_tokens -= removed.tokens


def _config_defaults(config: Dict[str, Any] | None) -> Dict[str, Any]:
    cfg = dict(config or {})
    max_passes = _normalize_int(cfg.get("max_passes", 3), 3, 1)
    token_limit = _normalize_int(cfg.get("token_limit", 0), 0, 0)
    clear_after = _normalize_int(cfg.get("clear_after", 0), 0, 0)
    prepend_mode = bool(cfg.get("prepend_mode", True))
    clear_on_build = bool(cfg.get("clear_on_build", False))
    enable_opt_in = bool(cfg.get("enable_opt_in", False))
    cache_id = (
        cfg.get("cache_id")
        or cfg.get("state_key")
        or cfg.get("_node_id")
        or "default"
    )
    return {
        "cache_id": str(cache_id),
        "max_passes": max_passes,
        "token_limit": token_limit,
        "clear_after": clear_after,
        "prepend_mode": prepend_mode,
        "clear_on_build": clear_on_build,
        "enable_opt_in": enable_opt_in,
    }


def op_cache(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _config_defaults(config)
    state = _cache.setdefault(cfg["cache_id"], CacheState())

    if state.generation != _build_generation:
        if cfg["clear_on_build"]:
            state.clear()
        state.generation = _build_generation

    if cfg["clear_after"] > 0 and state.passes_since_clear >= cfg["clear_after"]:
        state.clear()

    entries_added = False

    def add_entry(source: str, payload: Any) -> None:
        nonlocal entries_added
        entry = CacheEntry(payload=payload, tokens=_token_count(payload), source=source)
        state.history.append(entry)
        state.total_tokens += entry.tokens
        entries_added = True

    if "stream_in" in message:
        add_entry("stream_in", message["stream_in"])

    if cfg["enable_opt_in"] and "opt_in" in message:
        add_entry("opt_in", message["opt_in"])

    if entries_added:
        state.passes_since_clear += 1

    _trim_history(state, cfg["max_passes"], cfg["token_limit"])

    ordered = list(state.history)
    if not cfg["prepend_mode"]:
        ordered = list(reversed(ordered))

    stream_out = [entry.payload for entry in ordered]
    return {"stream_out": stream_out}


def build(container: Dict[str, Any]) -> None:
    global _build_generation
    _build_generation += 1
    container.setdefault("ops", {})["Cache"] = op_cache

