"""Custom exceptions for VOIDE graph engine."""
from __future__ import annotations

class GraphError(Exception):
    """Base class for graph-related errors."""
    pass

class CycleError(GraphError):
    """Raised when a cycle is detected in the graph."""
    pass

