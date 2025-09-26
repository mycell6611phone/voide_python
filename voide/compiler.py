"""Compile a Graph into a Runner and execute messages."""
from __future__ import annotations
from typing import Any, Dict, List

from voide.graph import Graph, Edge
from voide.errors import CycleError

class Runner:
    def __init__(self, graph: Graph, container: Dict[str, Any]) -> None:
        self.graph = graph
        self.container = container
        # map node->incoming edges
        self._in_edges: Dict[str, List[Edge]] = {}
        for e in graph.edges:
            self._in_edges.setdefault(e.to_node, []).append(e)

    def run(self, payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        outputs: Dict[str, Dict[str, Any]] = {}
        try:
            # topologically sort nodes (raises CycleError if cyclic)
            nodes = self.graph.topo_sort()
        except CycleError as e:
            raise RuntimeError(f"Cannot run: graph has cycles: {e}") from e

        for node in nodes:
            # collect inputs for this node
            msg: Dict[str, Any] = {}
            for e in self._in_edges.get(node.id, []):
                prev = outputs.get(e.from_node, {})
                if e.from_port in prev:
                    msg[e.to_port] = prev[e.from_port]
            # if no incoming edges, seed with the original payload
            if not self._in_edges.get(node.id):
                msg = dict(payload)

            # find the op to execute
            op = self.container.get("ops", {}).get(node.type_name)
            if not callable(op):
                raise RuntimeError(f"Unknown op: {node.type_name}")

            res = op(msg, node.config, self.container)
            if not isinstance(res, dict):
                raise RuntimeError(f"Op must return dict, got {type(res)}")

            outputs[node.id] = res

        return outputs

def compile(graph: Graph, container: Dict[str, Any]) -> Runner:
    """
    Factory to create a Runner for the given graph and container.
    """
    return Runner(graph, container)

