from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Dict, Tuple, List

from voide.graph import Graph, Node, Edge

# simple defaults per type
PORTS = {
    "Prompt": {"inputs": [], "outputs": ["prompt"]},
    "LLM": {"inputs": ["prompt"], "outputs": ["completion"]},
    "DebateLoop": {"inputs": ["task"], "outputs": ["completion"]},
    "Cache": {"inputs": ["prompt"], "outputs": ["prompt"]},
    "Log": {"inputs": ["data"], "outputs": []},
    "Memory": {"inputs": ["data"], "outputs": ["results"]},
    "Divider": {"inputs": ["route"], "outputs": ["A", "B"]},
    "ToolCall": {"inputs": ["args"], "outputs": ["result"]},
    "UI": {"inputs": [], "outputs": ["prompt"]},
}

@dataclass
class NodeWidget:
    id: str
    type_name: str
    x: int
    y: int
    config: dict
    rect: int
    label: int
    in_ports: Dict[str, int]
    out_ports: Dict[str, int]

class GraphCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, **kw):
        super().__init__(master, background="#1e1f22", highlightthickness=0, **kw)
        self.nodes: Dict[str, NodeWidget] = {}
        self.edges: List[tuple[str, str, str, str, int]] = []  # (from_id, from_port, to_id, to_port, line_id)
        self._drag: tuple[str, int, int] | None = None
        self._connecting: tuple[str, str, int] | None = None  # node_id, port_name, tmp_line_id
        self.bind("<ButtonPress-1>", self._on_down)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_up)

    # ---- node/port helpers ----
    def add_node(self, node_id: str, type_name: str, x: int, y: int, config: dict | None = None):
        cfg = config or {}
        w, h = 140, 60
        rect = self.create_rectangle(x, y, x + w, y + h, fill="#2b2d31", outline="#4e5157", width=2, tags=(f"node:{node_id}",))
        label = self.create_text(x + w / 2, y + 15, text=type_name, fill="#e6e6e6", font=("TkDefaultFont", 10, "bold"))
        # ports
        spec = PORTS.get(type_name, {"inputs": ["in"], "outputs": ["out"]})
        in_ports: Dict[str, int] = {}
        out_ports: Dict[str, int] = {}
        for i, name in enumerate(spec.get("inputs", [])):
            cy = y + 30 + i * 16
            pid = self.create_oval(x - 6, cy - 6, x + 6, cy + 6, fill="#3b82f6", outline="", tags=(f"port_in:{node_id}:{name}",))
            in_ports[name] = pid
        for i, name in enumerate(spec.get("outputs", [])):
            cy = y + 30 + i * 16
            pid = self.create_oval(x + w - 6, cy - 6, x + w + 6, cy + 6, fill="#22c55e", outline="", tags=(f"port_out:{node_id}:{name}",))
            out_ports[name] = pid
        self.nodes[node_id] = NodeWidget(node_id, type_name, x, y, cfg, rect, label, in_ports, out_ports)

    def ports_at(self, x: int, y: int) -> tuple[str, str] | None:
        items = self.find_overlapping(x, y, x, y)
        for it in items:
            for tag in self.gettags(it):
                if tag.startswith("port_in:"):
                    _, nid, pname = tag.split(":", 2)
                    return (nid, f"in:{pname}")
                if tag.startswith("port_out:"):
                    _, nid, pname = tag.split(":", 2)
                    return (nid, f"out:{pname}")
        return None

    # ---- events ----
    def _on_down(self, ev):
        hit = self.find_overlapping(ev.x, ev.y, ev.x, ev.y)
        # start connect if on a port
        pp = self.ports_at(ev.x, ev.y)
        if pp:
            nid, spec = pp
            kind, pname = spec.split(":", 1)
            if kind == "out":
                x0, y0, x1, y1 = self.bbox(self.nodes[nid].out_ports[pname])
                line = self.create_line((x0 + x1) / 2, (y0 + y1) / 2, ev.x, ev.y, fill="#94a3b8", width=2, arrow=tk.LAST)
                self._connecting = (nid, pname, line)
                return
        # else maybe drag node
        for it in hit:
            for tag in self.gettags(it):
                if tag.startswith("node:"):
                    nid = tag.split(":", 1)[1]
                    nx, ny = self.nodes[nid].x, self.nodes[nid].y
                    self._drag = (nid, ev.x - nx, ev.y - ny)
                    return

    def _on_drag(self, ev):
        if self._drag:
            nid, ox, oy = self._drag
            self.move_node(nid, ev.x - ox, ev.y - oy)
        elif self._connecting:
            _, _, line = self._connecting
            x0, y0, *_ = self.coords(line)
            self.coords(line, x0, y0, ev.x, ev.y)

    def _on_up(self, ev):
        if self._drag:
            self._drag = None
            return
        if self._connecting:
            src_nid, src_port, line = self._connecting
            self._connecting = None
            hit = self.ports_at(ev.x, ev.y)
            if not hit:
                self.delete(line)
                return
            dst_nid, spec = hit
            kind, dst_port = spec.split(":", 1)
            if kind != "in":
                self.delete(line)
                return
            # snap line to dst port center
            x0, y0, x1, y1 = self.bbox(self.nodes[src_nid].out_ports[src_port])
            sx, sy = (x0 + x1) / 2, (y0 + y1) / 2
            x0, y0, x1, y1 = self.bbox(self.nodes[dst_nid].in_ports[dst_port])
            dx, dy = (x0 + x1) / 2, (y0 + y1) / 2
            self.coords(line, sx, sy, dx, dy)
            self.edges.append((src_nid, src_port, dst_nid, dst_port, line))

    def move_node(self, node_id: str, x: int, y: int) -> None:
        n = self.nodes[node_id]
        dx, dy = x - n.x, y - n.y
        self.move(n.rect, dx, dy)
        self.move(n.label, dx, dy)
        for pid in list(n.in_ports.values()) + list(n.out_ports.values()):
            self.move(pid, dx, dy)
        n.x, n.y = x, y
        # update edges connected to this node
        for (a, ap, b, bp, line) in list(self.edges):
            if a == node_id:
                x0, y0, x1, y1 = self.bbox(n.out_ports[ap])
                sx, sy = (x0 + x1) / 2, (y0 + y1) / 2
                x0, y0, x1, y1 = self.bbox(self.nodes[b].in_ports[bp])
                dx2, dy2 = (x0 + x1) / 2, (y0 + y1) / 2
                self.coords(line, sx, sy, dx2, dy2)
            if b == node_id:
                x0, y0, x1, y1 = self.bbox(self.nodes[a].out_ports[ap])
                sx, sy = (x0 + x1) / 2, (y0 + y1) / 2
                x0, y0, x1, y1 = self.bbox(n.in_ports[bp])
                dx2, dy2 = (x0 + x1) / 2, (y0 + y1) / 2
                self.coords(line, sx, sy, dx2, dy2)

    # ---- graph conversion ----
    def to_graph(self) -> tuple[Graph, Dict[str, tuple[int, int]]]:
        g = Graph()
        for nid, nw in self.nodes.items():
            g.add_node(Node(id=nid, type_name=nw.type_name, config=nw.config))
        for a, ap, b, bp, _line in self.edges:
            g.add_edge(Edge(a, ap, b, bp))
        pos = {nid: (nw.x, nw.y) for nid, nw in self.nodes.items()}
        return g, pos

    def load_from(self, g: Graph, positions: Dict[str, tuple[int, int]]):
        # clear
        self.delete("all")
        self.nodes.clear()
        self.edges.clear()
        for nid, node in g.nodes.items():
            x, y = positions.get(nid, (50, 50))
            self.add_node(nid, node.type_name, x, y, node.config)
        for e in g.edges:
            a = self.nodes[e.from_node]
            b = self.nodes[e.to_node]
            x0, y0, x1, y1 = self.bbox(a.out_ports.get(e.from_port, list(a.out_ports.values())[0]))
            sx, sy = (x0 + x1) / 2, (y0 + y1) / 2
            x0, y0, x1, y1 = self.bbox(b.in_ports.get(e.to_port, list(b.in_ports.values())[0]))
            dx, dy = (x0 + x1) / 2, (y0 + y1) / 2
            line = self.create_line(sx, sy, dx, dy, fill="#94a3b8", width=2, arrow=tk.LAST)
            self.edges.append((e.from_node, e.from_port, e.to_node, e.to_port, line))
