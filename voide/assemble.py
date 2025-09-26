# File: workspace/voide/assemble.py
"""VOIDE assembler for Python chunks.

Loads chunk modules from a glob, validates their contract, resolves dependencies,
then calls build(container) for each in topological order.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .chunk_api import (
    ChunkMeta,
    UnresolvedDependenciesError,
    load_module,
    scan_chunk_files,
    topo_order,
    validate_and_meta,
)

def assemble(chunks_glob: str = "workspace/chunks/*.py", config: Dict | None = None) -> Dict:
    """Assemble a container from chunk files.

    Args:
        chunks_glob: Glob pattern of chunk python files.
        config: Optional configuration dict, available at container["config"].

    Returns:
        container dict with registered objects.
    """
    container: Dict = {"config": dict(config or {}), "ops": {}, "tools": {}}

    files = scan_chunk_files(chunks_glob)
    modules_meta: List[Tuple[object, ChunkMeta]] = []
    for p in files:
        if Path(p).name.startswith("_"):
            try:
                mod = load_module(Path(p))
                meta = validate_and_meta(mod, Path(p))
            except Exception:
                continue
        mod = load_module(Path(p))
        meta = validate_and_meta(mod, Path(p))
        modules_meta.append((mod, meta))

    ordered = topo_order(modules_meta, initial_keys=container.keys())

    for mod, meta in ordered:
        mod.build(container)  # type: ignore[attr-defined]
        for k in meta.provides:
            container.setdefault(k, getattr(mod, k, container.get(k)))

    return container

__all__ = ["assemble", "UnresolvedDependenciesError"]
