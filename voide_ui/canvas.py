from __future__ import annotations

import copy
import tkinter as tk
from tkinter import font as tkfont
from dataclasses import dataclass
from typing import Dict, Tuple, List, Callable
from voide.graph import Graph, Node, Edge

# simple defaults per type
PORTS = {
    "Prompt": {"inputs": [], "outputs": ["prompt"]},
    "LLM": {"inputs": ["prompt"], "outputs": ["completion"]},
    "DebateLoop": {"inputs": ["task"], "outputs": ["completion"]},
    "Cache": {
        "inputs": ["stream_in"],
        "optional_inputs": ["opt_in"],
        "outputs": ["stream_out"],
    },
    "Log": {"inputs": ["data"], "outputs": []},
    "Memory": {"inputs": ["data"], "outputs": ["results"]},
    "Divider": {"inputs": ["route"], "outputs": ["A", "B"]},
    "ToolCall": {"inputs": ["args"], "outputs": ["result"]},
    "UI": {"inputs": ["response"], "outputs": ["prompt"]},
}

NODE_WIDTH = 180
NODE_HEIGHT = 110
PORT_SPACING = 24
PORT_START_Y = 44

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
    in_order: List[str]
    out_order: List[str]

class GraphCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, **kw):
        super().__init__(master, background="#1e1f22", highlightthickness=0, **kw)
        self.nodes: Dict[str, NodeWidget] = {}
        self.edges: List[tuple[str, str, str, str, int]] = []  # (from_id, from_port, to_id, to_port, line_id)
        self._drag: tuple[str, int, int, int, int] | None = None
        self._connecting: tuple[str, str, int] | None = None  # node_id, port_name, tmp_line_id
        self._dragging = False
        self._click_target: str | None = None
        self._click_start: tuple[int, int] | None = None
        self._clipboard: dict | None = None
        self._paste_count = 0
        self._context_target: str | None = None
        self._context_menu_pos: tuple[int, int] | None = None
        self._label_font = tkfont.nametofont("TkDefaultFont").copy()
        self._label_font.configure(weight="bold")
        self._context_menu = tk.Menu(self, tearoff=False)
        self._context_menu.add_command(label="Cut", command=self._context_cut)
        self._context_menu.add_command(label="Copy", command=self._context_copy)
        self._context_menu.add_command(label="Paste", command=self._context_paste)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Delete", command=self._context_delete)
        self._context_menu.add_command(label="Reverse Inputs", command=self._context_reverse_inputs)

        self.node_click_callback: Callable[[str, NodeWidget], None] | None = None
        self._label_font = tkfont.nametofont("TkDefaultFont").copy()
        self._label_font.configure(weight="bold")

        self.bind("<ButtonPress-1>", self._on_down)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_up)
        self.bind("<ButtonPress-3>", self._on_context)

    def set_label_font_family(self, family: str) -> None:
        if not family:
            return
        try:
            current = self._label_font.cget("family")
        except tk.TclError:
            current = None
        if current == family:
            return
        self._label_font.configure(family=family)
        for node in self.nodes.values():
            self.itemconfigure(node.label, font=self._label_font)

    # ---- node/port helpers ----
    def add_node(self, node_id: str, type_name: str, x: int, y: int, config: dict | None = None):
        cfg = config or {}
        w, h = NODE_WIDTH, NODE_HEIGHT
        rect = self.create_rectangle(x, y, x + w, y + h, fill="#2b2d31", outline="#4e5157", width=2, tags=(f"node:{node_id}",))

        label = self.create_text(x + w / 2, y + 30, text=type_name, fill="#e6e6e6", font=self._label_font)

        # ports
        spec = PORTS.get(type_name, {"inputs": ["in"], "outputs": ["out"]})
        in_ports: Dict[str, int] = {}
        out_ports: Dict[str, int] = {}
        in_order: List[str] = []
        out_order: List[str] = []
        for i, name in enumerate(spec.get("inputs", [])):
            cy = y + PORT_START_Y + i * PORT_SPACING
            pid = self.create_oval(x - 8, cy - 8, x + 8, cy + 8, fill="#3b82f6", outline="", tags=(f"port_in:{node_id}:{name}",))
            in_ports[name] = pid
            in_order.append(name)
        optional_inputs = spec.get("optional_inputs", [])
        if optional_inputs:
            opt_spacing = 24
            base_x = x + w / 2 - opt_spacing * (len(optional_inputs) - 1) / 2
            cy = y + h - 16
            for idx, name in enumerate(optional_inputs):
                cx = base_x + idx * opt_spacing
                pid = self.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#38bdf8", outline="", tags=(f"port_in:{node_id}:{name}",))
                in_ports[name] = pid
                in_order.append(name)
        for i, name in enumerate(spec.get("outputs", [])):
            cy = y + PORT_START_Y + i * PORT_SPACING
            pid = self.create_oval(x + w - 8, cy - 8, x + w + 8, cy + 8, fill="#22c55e", outline="", tags=(f"port_out:{node_id}:{name}",))
            out_ports[name] = pid
            out_order.append(name)
        self.nodes[node_id] = NodeWidget(node_id, type_name, x, y, cfg, rect, label, in_ports, out_ports, in_order, out_order)
        if hasattr(self.master, "register_node"):
            try:
                self.master.register_node(node_id)  # type: ignore[attr-defined]
            except Exception:
                pass

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

    def node_at(self, x: int, y: int) -> str | None:
        items = self.find_overlapping(x, y, x, y)
        for it in items:
            for tag in self.gettags(it):
                if tag.startswith("node:"):
                    return tag.split(":", 1)[1]
                if tag.startswith("port_in:") or tag.startswith("port_out:"):
                    parts = tag.split(":", 2)
                    if len(parts) >= 3:
                        return parts[1]
        return None

    def _port_center(self, pid: int) -> tuple[float, float]:
        x0, y0, x1, y1 = self.bbox(pid)
        return (x0 + x1) / 2, (y0 + y1) / 2

    def _update_edges_for_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        for idx, (a, ap, b, bp, line) in enumerate(list(self.edges)):
            if a == node_id and ap in self.nodes[a].out_ports and b in self.nodes:
                sx, sy = self._port_center(self.nodes[a].out_ports[ap])
                dx, dy = self._port_center(self.nodes[b].in_ports[bp])
                self.coords(line, sx, sy, dx, dy)
            elif b == node_id and bp in self.nodes[b].in_ports and a in self.nodes:
                sx, sy = self._port_center(self.nodes[a].out_ports[ap])
                dx, dy = self._port_center(self.nodes[b].in_ports[bp])
                self.coords(line, sx, sy, dx, dy)

    def remove_node(self, node_id: str) -> None:
        n = self.nodes.pop(node_id, None)
        if not n:
            return
        self.delete(n.rect)
        self.delete(n.label)
        for pid in list(n.in_ports.values()) + list(n.out_ports.values()):
            self.delete(pid)
        for edge in list(self.edges):
            if edge[0] == node_id or edge[2] == node_id:
                self.delete(edge[4])
                self.edges.remove(edge)
        if hasattr(self.master, "close_option_window"):
            try:
                self.master.close_option_window(node_id)  # type: ignore[attr-defined]
            except Exception:
                pass

    # ---- events ----
    def _on_down(self, ev):
        self._click_target = None
        self._click_start = (ev.x, ev.y)
        self._dragging = False
        hit = self.find_overlapping(ev.x, ev.y, ev.x, ev.y)
        # start connect if on a port
        pp = self.ports_at(ev.x, ev.y)
        if pp:
            nid, spec = pp
            kind, pname = spec.split(":", 1)
            if kind == "out":
                sx, sy = self._port_center(self.nodes[nid].out_ports[pname])
                line = self.create_line(sx, sy, ev.x, ev.y, fill="#94a3b8", width=2, arrow=tk.LAST)
                self._connecting = (nid, pname, line)
                return
        # else maybe drag node
        for it in hit:
            for tag in self.gettags(it):
                if tag.startswith("node:"):
                    nid = tag.split(":", 1)[1]
                    nx, ny = self.nodes[nid].x, self.nodes[nid].y

                    self._drag = (nid, ev.x - nx, ev.y - ny, nx, ny)
                    self._click_target = nid

                    return

    def _on_drag(self, ev):
        if self._drag:

            nid, ox, oy, _start_x, _start_y = self._drag
            self._dragging = True

            self.move_node(nid, ev.x - ox, ev.y - oy)
        elif self._connecting:
            _, _, line = self._connecting
            x0, y0, *_ = self.coords(line)
            self.coords(line, x0, y0, ev.x, ev.y)
        if self._click_start and (abs(ev.x - self._click_start[0]) > 4 or abs(ev.y - self._click_start[1]) > 4):
            self._click_target = None

    def _on_up(self, ev):

        had_drag = self._dragging
        self._dragging = False

        if self._drag:
            nid, _ox, _oy, start_x, start_y = self._drag
            moved = abs(self.nodes[nid].x - start_x) > 2 or abs(self.nodes[nid].y - start_y) > 2
            self._drag = None
            if not moved and self.node_click_callback:
                self.node_click_callback(nid, self.nodes[nid])
            return

        connection_active = False
        if self._connecting:
            connection_active = True
            src_nid, src_port, line = self._connecting
            self._connecting = None
            hit = self.ports_at(ev.x, ev.y)
            if not hit:
                self.delete(line)
            else:
                dst_nid, spec = hit
                kind, dst_port = spec.split(":", 1)
                if kind != "in":
                    self.delete(line)
                else:
                    sx, sy = self._port_center(self.nodes[src_nid].out_ports[src_port])
                    dx, dy = self._port_center(self.nodes[dst_nid].in_ports[dst_port])
                    self.coords(line, sx, sy, dx, dy)
                    self.edges.append((src_nid, src_port, dst_nid, dst_port, line))
        if self._click_target and not had_drag and not connection_active:
            self.event_generate("<<NodeClick>>", data=self._click_target)
        self._click_target = None
        self._click_start = None

    def move_node(self, node_id: str, x: int, y: int) -> None:
        n = self.nodes[node_id]
        dx, dy = x - n.x, y - n.y
        self.move(n.rect, dx, dy)
        self.move(n.label, dx, dy)
        for pid in list(n.in_ports.values()) + list(n.out_ports.values()):
            self.move(pid, dx, dy)
        n.x, n.y = x, y
        self._update_edges_for_node(node_id)

    def reverse_inputs(self, node_id: str) -> None:
        n = self.nodes.get(node_id)
        if not n or len(n.in_order) < 2:
            return
        new_order = list(reversed(n.in_order))
        for idx, name in enumerate(new_order):
            pid = n.in_ports[name]
            cx, _ = self._port_center(pid)
            cy = n.y + PORT_START_Y + idx * PORT_SPACING
            self.coords(pid, cx - 8, cy - 8, cx + 8, cy + 8)
        n.in_order = new_order
        self._update_edges_for_node(node_id)

    # ---- context menu ----
    def _on_context(self, ev):
        self._context_target = self.node_at(ev.x, ev.y)
        self._context_menu_pos = (ev.x, ev.y)
        self._update_context_menu_state()
        try:
            self._context_menu.tk_popup(ev.x_root, ev.y_root)
        finally:
            self._context_menu.grab_release()

    def _update_context_menu_state(self):
        has_node = self._context_target is not None
        has_inputs = False
        if has_node and self._context_target in self.nodes:
            has_inputs = len(self.nodes[self._context_target].in_order) > 1
        states = {
            "Cut": tk.NORMAL if has_node else tk.DISABLED,
            "Copy": tk.NORMAL if has_node else tk.DISABLED,
            "Delete": tk.NORMAL if has_node else tk.DISABLED,
            "Reverse Inputs": tk.NORMAL if has_node and has_inputs else tk.DISABLED,
            "Paste": tk.NORMAL if self._clipboard else tk.DISABLED,
        }
        for idx, label in enumerate(["Cut", "Copy", "Paste", None, "Delete", "Reverse Inputs"]):
            if label is None:
                continue
            state = states[label]
            self._context_menu.entryconfig(label, state=state)

    def _context_copy(self):
        if not self._context_target:
            return
        if self._context_target not in self.nodes:
            return
        n = self.nodes[self._context_target]
        self._clipboard = {
            "type": n.type_name,
            "config": copy.deepcopy(n.config),
        }

    def _context_cut(self):
        self._context_copy()
        if self._context_target:
            self.remove_node(self._context_target)

    def _context_paste(self):
        if not self._clipboard:
            return
        pos = self._context_menu_pos or (80, 80)
        cx, cy = pos
        self._paste_count += 1
        offset = (self._paste_count % 5) * 20
        x = int(cx - NODE_WIDTH / 2 + offset)
        y = int(cy - NODE_HEIGHT / 2 + offset)
        if hasattr(self.master, "next_node_id"):
            try:
                new_id = self.master.next_node_id()  # type: ignore[attr-defined]
            except Exception:
                new_id = self._generate_local_id()
        else:
            new_id = self._generate_local_id()
        self.add_node(new_id, self._clipboard["type"], x, y, config=copy.deepcopy(self._clipboard.get("config", {})))

    def _generate_local_id(self) -> str:
        base = 1
        while True:
            candidate = f"copy{base}"
            if candidate not in self.nodes:
                return candidate
            base += 1

    def _context_delete(self):
        if not self._context_target:
            return
        self.remove_node(self._context_target)

    def _context_reverse_inputs(self):
        if not self._context_target:
            return
        self.reverse_inputs(self._context_target)

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
            out_pid = a.out_ports.get(e.from_port, next(iter(a.out_ports.values())))
            in_pid = b.in_ports.get(e.to_port, next(iter(b.in_ports.values())))
            sx, sy = self._port_center(out_pid)
            dx, dy = self._port_center(in_pid)
            line = self.create_line(sx, sy, dx, dy, fill="#94a3b8", width=2, arrow=tk.LAST)
            self.edges.append((e.from_node, e.from_port, e.to_node, e.to_port, line))
