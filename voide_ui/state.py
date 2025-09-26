from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from voide.graph import Graph, Node, Edge


@dataclass
class NodeState:
    id: str
    type_name: str
    x: int
    y: int
    config: Dict[str, Any]


@dataclass
class EdgeState:
    from_node: str
    from_port: str
    to_node: str
    to_port: str


@dataclass
class GraphState:
    nodes: List[NodeState]
    edges: List[EdgeState]


def graph_to_state(g: Graph, positions: Dict[str, Tuple[int, int]]) -> GraphState:
    nodes: List[NodeState] = []
    for nid, n in g.nodes.items():
        x, y = positions.get(nid, (50, 50))
        nodes.append(NodeState(id=n.id, type_name=n.type_name, x=x, y=y, config=n.config))
    edges: List[EdgeState] = [EdgeState(e.from_node, e.from_port, e.to_node, e.to_port) for e in g.edges]
    return GraphState(nodes=nodes, edges=edges)


def state_to_graph(state: GraphState) -> tuple[Graph, Dict[str, Tuple[int, int]]]:
    g = Graph()
    pos: Dict[str, Tuple[int, int]] = {}
    for ns in state.nodes:
        g.add_node(Node(id=ns.id, type_name=ns.type_name, config=ns.config))
        pos[ns.id] = (ns.x, ns.y)
    for es in state.edges:
        g.add_edge(Edge(es.from_node, es.from_port, es.to_node, es.to_port))
    return g, pos


def save_graph(path: str, g: Graph, positions: Dict[str, Tuple[int, int]]) -> None:
    state = graph_to_state(g, positions)
    payload = {
        "nodes": [asdict(n) for n in state.nodes],
        "edges": [asdict(e) for e in state.edges],
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_graph(path: str) -> tuple[Graph, Dict[str, Tuple[int, int]]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes = [NodeState(**nd) for nd in data.get("nodes", [])]
    edges = [EdgeState(**ed) for ed in data.get("edges", [])]
    return state_to_graph(GraphState(nodes=nodes, edges=edges))
