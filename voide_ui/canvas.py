from __future__ import annotations

import copy
import tkinter as tk
from tkinter import font as tkfont
from dataclasses import dataclass, field
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
PORT_RADIUS = 8
OPTIONAL_PORT_SPACING = 24
OPTIONAL_PORT_OFFSET_Y = 16
LABEL_OFFSET_Y = 30

@dataclass
class NodeWidget:
    id: str
    type_name: str
    x: float
    y: float
    config: dict
    rect: int
    label: int
    in_ports: Dict[str, int]
    out_ports: Dict[str, int]
    in_order: List[str]
    out_order: List[str]
    optional_inputs: List[str] = field(default_factory=list)

class GraphCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, **kw):
        super().__init__(master, background="#1e1f22", highlightthickness=0, **kw)
        self.nodes: Dict[str, NodeWidget] = {}
        self.edges: List[tuple[str, str, str, str, int]] = []  # (from_id, from_port, to_id, to_port, line_id)
        self._drag: tuple[str, float, float, float, float] | None = None
        self._connecting: tuple[str, str, int] | None = None  # node_id, port_name, tmp_line_id
        self._dragging = False
        self._click_target: str | None = None
        self._click_start: tuple[int, int] | None = None
        self._clipboard: dict | None = None
        self._paste_count = 0
        self._context_target: str | None = None
        self._context_menu_pos: tuple[float, float] | None = None
        self._label_font = tkfont.nametofont("TkDefaultFont").copy()
        self._label_font.configure(weight="bold")
        try:
            self._base_label_font_size = int(self._label_font.cget("size"))
        except tk.TclError:
            self._base_label_font_size = 12

        self._scale = 1.0
        self._min_scale = 0.5
        self._max_scale = 2.5
        self._origin_x = 0.0
        self._origin_y = 0.0

        self._context_menu = tk.Menu(self, tearoff=False)
        self._context_menu.add_command(label="Cut", command=self._context_cut)
        self._context_menu.add_command(label="Copy", command=self._context_copy)
        self._context_menu.add_command(label="Paste", command=self._context_paste)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Delete", command=self._context_delete)
        self._context_menu.add_command(label="Reverse Inputs", command=self._context_reverse_inputs)

        self.node_click_callback: Callable[[str, NodeWidget], None] | None = None
        self._apply_font_to_labels()

        self.bind("<ButtonPress-1>", self._on_down)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_up)
        self.bind("<ButtonPress-3>", self._on_context)
        self.bind("<Control-MouseWheel>", self._on_zoom)
        self.bind("<Control-Button-4>", self._on_zoom_button)
        self.bind("<Control-Button-5>", self._on_zoom_button)

    def set_label_font_family(self, family: str) -> None:
        if not family:
            return
        try:
            current = self._label_font.cget("family")
        except tk.TclError:
            current = None
        if current == family:
            return
        try:
            self._label_font.configure(family=family)
        except tk.TclError:
            return
        self._apply_font_to_labels()

    def _scale_length(self, value: float) -> float:
        return value * self._scale

    def _world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        return (x - self._origin_x) * self._scale, (y - self._origin_y) * self._scale

    def _screen_to_world(self, x: float, y: float) -> tuple[float, float]:
        return x / self._scale + self._origin_x, y / self._scale + self._origin_y

    def _update_label_font_scale(self) -> None:
        base = self._base_label_font_size
        if base == 0:
            return
        if base > 0:
            size = max(6, int(round(base * self._scale)))
        else:
            size = min(-6, int(round(base * self._scale)))
        try:
            self._label_font.configure(size=size)
        except tk.TclError:
            pass

    def _apply_font_to_labels(self) -> None:
        self._update_label_font_scale()
        for node in self.nodes.values():
            self.itemconfigure(node.label, font=self._label_font)

    def _update_node_visuals(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        sx, sy = self._world_to_screen(node.x, node.y)
        w = self._scale_length(NODE_WIDTH)
        h = self._scale_length(NODE_HEIGHT)

        self.coords(node.rect, sx, sy, sx + w, sy + h)
        self.coords(node.label, sx + w / 2, sy + self._scale_length(LABEL_OFFSET_Y))

        radius = self._scale_length(PORT_RADIUS)
        port_start = self._scale_length(PORT_START_Y)
        port_spacing = self._scale_length(PORT_SPACING)

        for idx, name in enumerate(node.in_order):
            pid = node.in_ports.get(name)
            if pid is None:
                continue
            cy = sy + port_start + idx * port_spacing
            self.coords(pid, sx - radius, cy - radius, sx + radius, cy + radius)

        if node.optional_inputs:
            opt_spacing = self._scale_length(OPTIONAL_PORT_SPACING)
            cy = sy + h - self._scale_length(OPTIONAL_PORT_OFFSET_Y)
            base_cx = sx + w / 2 - opt_spacing * (len(node.optional_inputs) - 1) / 2
            for idx, name in enumerate(node.optional_inputs):
                pid = node.in_ports.get(name)
                if pid is None:
                    continue
                cx = base_cx + idx * opt_spacing
                self.coords(pid, cx - radius, cy - radius, cx + radius, cy + radius)

        for idx, name in enumerate(node.out_order):
            pid = node.out_ports.get(name)
            if pid is None:
                continue
            cy = sy + port_start + idx * port_spacing
            cx = sx + w
            self.coords(pid, cx - radius, cy - radius, cx + radius, cy + radius)

    # ---- node/port helpers ----
    def add_node(
        self,
        node_id: str,
        type_name: str,
        x: float,
        y: float,
        config: dict | None = None,
        *,
        from_world: bool = False,
    ):
        cfg = config or {}
        spec = PORTS.get(type_name, {"inputs": ["in"], "outputs": ["out"]})
        in_ports: Dict[str, int] = {}
        out_ports: Dict[str, int] = {}
        in_order: List[str] = list(spec.get("inputs", []))
        optional_inputs: List[str] = list(spec.get("optional_inputs", []))
        out_order: List[str] = list(spec.get("outputs", []))

        if from_world:
            wx, wy = float(x), float(y)
            sx, sy = self._world_to_screen(wx, wy)
        else:
            sx, sy = float(x), float(y)
            wx, wy = self._screen_to_world(sx, sy)

        w, h = self._scale_length(NODE_WIDTH), self._scale_length(NODE_HEIGHT)
        rect = self.create_rectangle(
            sx,
            sy,
            sx + w,
            sy + h,
            fill="#2b2d31",
            outline="#4e5157",
            width=2,
            tags=(f"node:{node_id}",),
        )

        label = self.create_text(
            sx + w / 2,
            sy + self._scale_length(LABEL_OFFSET_Y),
            text=type_name,
            fill="#e6e6e6",
            font=self._label_font,
        )

        radius = self._scale_length(PORT_RADIUS)
        port_start = self._scale_length(PORT_START_Y)
        port_spacing = self._scale_length(PORT_SPACING)

        for idx, name in enumerate(in_order):
            cy = sy + port_start + idx * port_spacing
            pid = self.create_oval(
                sx - radius,
                cy - radius,
                sx + radius,
                cy + radius,
                fill="#3b82f6",
                outline="",
                tags=(f"port_in:{node_id}:{name}",),
            )
            in_ports[name] = pid

        if optional_inputs:
            opt_spacing = self._scale_length(OPTIONAL_PORT_SPACING)
            base_cx = sx + w / 2 - opt_spacing * (len(optional_inputs) - 1) / 2
            cy = sy + h - self._scale_length(OPTIONAL_PORT_OFFSET_Y)
            for idx, name in enumerate(optional_inputs):
                cx = base_cx + idx * opt_spacing
                pid = self.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    fill="#38bdf8",
                    outline="",
                    tags=(f"port_in:{node_id}:{name}", "port_optional"),
                )
                in_ports[name] = pid

        for idx, name in enumerate(out_order):
            cy = sy + port_start + idx * port_spacing
            cx = sx + w
            pid = self.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                fill="#22c55e",
                outline="",
                tags=(f"port_out:{node_id}:{name}",),
            )
            out_ports[name] = pid

        self.nodes[node_id] = NodeWidget(
            node_id,
            type_name,
            wx,
            wy,
            cfg,
            rect,
            label,
            in_ports,
            out_ports,
            in_order,
            out_order,
            optional_inputs,
        )
        self._apply_font_to_labels()
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
                    node = self.nodes[nid]
                    wx, wy = self._screen_to_world(ev.x, ev.y)
                    self._drag = (nid, wx - node.x, wy - node.y, node.x, node.y)
                    self._click_target = nid

                    return

    def _on_drag(self, ev):
        if self._drag:

            nid, ox, oy, _start_x, _start_y = self._drag
            self._dragging = True

            wx, wy = self._screen_to_world(ev.x, ev.y)
            self.move_node(nid, wx - ox, wy - oy)
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
            node = self.nodes[nid]
            dx = abs(node.x - start_x) * self._scale
            dy = abs(node.y - start_y) * self._scale
            moved = dx > 2 or dy > 2
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

    def _on_zoom(self, ev):
        delta = getattr(ev, "delta", 0)
        if delta == 0:
            return "break"
        direction = 1 if delta > 0 else -1
        self._apply_zoom(direction, ev.x, ev.y)
        return "break"

    def _on_zoom_button(self, ev):
        num = getattr(ev, "num", None)
        if num is None:
            return "break"
        direction = 1 if num == 4 else -1
        self._apply_zoom(direction, ev.x, ev.y)
        return "break"

    def _apply_zoom(self, direction: int, sx: float, sy: float) -> None:
        if direction == 0:
            return
        factor = 1.1 if direction > 0 else 1 / 1.1
        new_scale = max(self._min_scale, min(self._max_scale, self._scale * factor))
        if abs(new_scale - self._scale) < 1e-6:
            return
        wx, wy = self._screen_to_world(sx, sy)
        self._scale = new_scale
        self._origin_x = wx - sx / self._scale
        self._origin_y = wy - sy / self._scale
        self._apply_font_to_labels()
        for nid in list(self.nodes.keys()):
            self._update_node_visuals(nid)
        for nid in list(self.nodes.keys()):
            self._update_edges_for_node(nid)
        if self._connecting:
            src_nid, src_port, line = self._connecting
            if src_nid in self.nodes and src_port in self.nodes[src_nid].out_ports:
                sx0, sy0 = self._port_center(self.nodes[src_nid].out_ports[src_port])
                self.coords(line, sx0, sy0, sx, sy)

    def move_node(self, node_id: str, x: float, y: float) -> None:
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        node.x = float(x)
        node.y = float(y)
        self._update_node_visuals(node_id)
        self._update_edges_for_node(node_id)

    def reverse_inputs(self, node_id: str) -> None:
        n = self.nodes.get(node_id)
        if not n or len(n.in_order) < 2:
            return
        n.in_order = list(reversed(n.in_order))
        self._update_node_visuals(node_id)
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
        wx, wy = self._screen_to_world(cx, cy)
        self._paste_count += 1
        offset = (self._paste_count % 5) * 20
        x = wx - NODE_WIDTH / 2 + offset
        y = wy - NODE_HEIGHT / 2 + offset
        if hasattr(self.master, "next_node_id"):
            try:
                new_id = self.master.next_node_id()  # type: ignore[attr-defined]
            except Exception:
                new_id = self._generate_local_id()
        else:
            new_id = self._generate_local_id()
        self.add_node(
            new_id,
            self._clipboard["type"],
            x,
            y,
            config=copy.deepcopy(self._clipboard.get("config", {})),
            from_world=True,
        )

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
            self.add_node(nid, node.type_name, x, y, node.config, from_world=True)
        for e in g.edges:
            a = self.nodes[e.from_node]
            b = self.nodes[e.to_node]
            out_pid = a.out_ports.get(e.from_port, next(iter(a.out_ports.values())))
            in_pid = b.in_ports.get(e.to_port, next(iter(b.in_ports.values())))
            sx, sy = self._port_center(out_pid)
            dx, dy = self._port_center(in_pid)
            line = self.create_line(sx, sy, dx, dy, fill="#94a3b8", width=2, arrow=tk.LAST)
            self.edges.append((e.from_node, e.from_port, e.to_node, e.to_port, line))
