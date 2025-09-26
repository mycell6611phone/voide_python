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


DEFAULT_CHUNKS_GLOB = str((Path(__file__).resolve().parent.parent / "chunks" / "*.py"))

def assemble(chunks_glob: str | None = None, config: Dict | None = None) -> Dict:
    """Assemble a container from chunk files.

    Args:
        chunks_glob: Glob pattern of chunk python files. Defaults to the
            repository ``chunks`` directory when ``None``.
        config: Optional configuration dict, available at container["config"].

    Returns:
        container dict with registered objects.
    """
    if chunks_glob is None:
        chunks_glob = DEFAULT_CHUNKS_GLOB

    container: Dict = {"config": dict(config or {}), "ops": {}, "tools": {}}

    files = scan_chunk_files(chunks_glob)
    modules_meta: List[Tuple[object, ChunkMeta]] = []
    for p in files:
        path = Path(p)
        if path.name.startswith("_"):
            # Hidden modules (prefixed with "_") are considered opt-in and
            # should not be loaded by default.
            continue

        mod = load_module(path)
        meta = validate_and_meta(mod, path)
        modules_meta.append((mod, meta))

    ordered = topo_order(modules_meta, initial_keys=container.keys())

    for mod, meta in ordered:
        mod.build(container)  # type: ignore[attr-defined]
        for k in meta.provides:
            container.setdefault(k, getattr(mod, k, container.get(k)))

    return container

__all__ = ["assemble", "UnresolvedDependenciesError"]
