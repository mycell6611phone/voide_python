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
            incoming = self._in_edges.get(node.id, [])

            # collect inputs for this node
            msg: Dict[str, Any] = {}
            if incoming:
                for edge in incoming:
                    prev = outputs.get(edge.from_node)
                    if prev is None:
                        raise RuntimeError(
                            f"Upstream node '{edge.from_node}' has not produced outputs"
                        )

                    if edge.from_port in prev:
                        value = prev[edge.from_port]
                    else:
                        found = False
                        source_node = self.graph.nodes.get(edge.from_node)
                        if source_node and source_node.outputs:
                            mapped_key = source_node.outputs.get(edge.from_port)
                            if mapped_key is not None and mapped_key in prev:
                                value = prev[mapped_key]
                                found = True

                        if not found and len(prev) == 1:
                            value = next(iter(prev.values()))
                            found = True

                        if not found:
                            raise RuntimeError(
                                "Cannot map edge from port "
                                f"'{edge.from_port}' in outputs of '{edge.from_node}'"
                            )
                    msg[edge.to_port] = value

                if len(incoming) == 1:
                    source_outputs = outputs[incoming[0].from_node]
                    for key, value in source_outputs.items():
                        msg.setdefault(key, value)
            else:
                # if no incoming edges, seed with the original payload
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

