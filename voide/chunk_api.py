# File: workspace/voide/chunk_api.py
"""Chunk API helpers for VOIDE.

Contract per chunk module:
- provides: list[str]
- requires: list[str]
- def build(container: dict) -> None

All wiring happens inside build(). Import-time side effects are discouraged.
"""
from __future__ import annotations

import glob
from dataclasses import dataclass
from glob import glob as _glob
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Tuple


class ChunkLoadError(RuntimeError):
    pass


class ChunkValidationError(ValueError):
    pass


class UnresolvedDependenciesError(RuntimeError):
    def __init__(self, missing: dict[str, set[str]]):
        self.missing = missing
        super().__init__(f"Unresolved dependencies: {missing}")


@dataclass(frozen=True)
class ChunkMeta:
    path: Path
    provides: Tuple[str, ...]
    requires: Tuple[str, ...]


def load_module(path: Path) -> ModuleType:
    """Safely load a module from a file path without adding to sys.path.

    The module name is derived from the filename stem and a short hash of the path
    to avoid collisions if loaded multiple times from different locations.
    """
    path = path.resolve()
    if not path.exists():
        raise ChunkLoadError(f"Missing module file: {path}")
    name = f"voide_chunk_{path.stem}{abs(hash(str(path))) & 0xFFFF:X}"
    spec = spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ChunkLoadError(f"Cannot create spec for: {path}")
    mod = module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[assignment]
    except Exception as e:
        raise ChunkLoadError(f"Error importing {path}: {e}") from e
    return mod


def as_list(value: object, field: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        out: List[str] = []
        for v in value:
            if not isinstance(v, str):
                raise ChunkValidationError(f"{field} items must be str, got {type(v)}")
            out.append(v)
        return out
    raise ChunkValidationError(f"{field} must be list[str] or tuple[str,...]")


def validate_and_meta(mod: ModuleType, path: Path) -> ChunkMeta:
    provides = as_list(getattr(mod, "provides", []), "provides")
    requires = as_list(getattr(mod, "requires", []), "requires")
    build = getattr(mod, "build", None)
    if not callable(build):
        raise ChunkValidationError("build(container: dict) callable is required")
    return ChunkMeta(path=path, provides=tuple(provides), requires=tuple(requires))


def scan_chunk_files(glob_pattern: str) -> List[Path]:

    """Return a sorted list of chunk files for the given glob pattern."""

    if not glob_pattern:
        return []

    paths = (
        Path(p)
        for p in _glob(glob_pattern, recursive=True)
    )
    return sorted(path for path in paths if path.is_file())


def topo_order(mods: List[Tuple[ModuleType, ChunkMeta]], initial_keys: Iterable[str]) -> List[Tuple[ModuleType, ChunkMeta]]:
    """Return a buildable order or raise UnresolvedDependenciesError.

    We do a simple Kahn-like loop using the container keys as the available set.
    """
    available = set(initial_keys)
    pending = list(mods)
    ordered: List[Tuple[ModuleType, ChunkMeta]] = []
    last_len = None
    while pending and last_len != len(pending):
        last_len = len(pending)
        for pair in list(pending):
            mod, meta = pair
            if set(meta.requires).issubset(available):
                ordered.append(pair)
                available.update(meta.provides)
                pending.remove(pair)
    if pending:
        missing: dict[str, set[str]] = {}
        for m, meta in pending:
            missing[str(meta.path)] = set(meta.requires) - set(available)
        raise UnresolvedDependenciesError(missing)
    return ordered

