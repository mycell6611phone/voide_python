"""Namespace bridge exposing project chunk modules under :mod:`voide.chunks`."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from types import ModuleType
from typing import Iterable

import chunks as _top_level_chunks

__path__ = list(_top_level_chunks.__path__)
__all__ = sorted(
    name
    for _, name, is_pkg in pkgutil.iter_modules(_top_level_chunks.__path__)
    if not is_pkg and not name.startswith("_")
)


def _load(name: str) -> ModuleType:
    module = importlib.import_module(f"chunks.{name}")
    sys.modules.setdefault(f"{__name__}.{name}", module)
    return module


def __getattr__(name: str) -> ModuleType:
    if name in __all__:
        return _load(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> Iterable[str]:
    return sorted(set(globals()) | set(__all__))


for _name in __all__:
    _load(_name)
