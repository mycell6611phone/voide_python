from .assemble import assemble, UnresolvedDependenciesError  # re-export

__all__ = ["assemble", "UnresolvedDependenciesError"]

try:
    from . import chunks as chunks  # type: ignore[attr-defined]
except (ModuleNotFoundError, ImportError):  # pragma: no cover - optional dependency
    chunks = None  # type: ignore[assignment]
else:
    __all__.append("chunks")







