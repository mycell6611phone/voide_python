# write_step6_ui.py
from pathlib import Path

files = {
"workspace/voide_ui/__init__.py": "",
"workspace/voide_ui/state.py": """from __future__ import annotations

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
""",
"workspace/voide_ui/canvas.py": """from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Dict, Tuple, List

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
        optional_inputs = spec.get("optional_inputs", [])
        if optional_inputs:
            opt_spacing = 20
            base_x = x + w / 2 - opt_spacing * (len(optional_inputs) - 1) / 2
            cy = y + h - 10
            for idx, name in enumerate(optional_inputs):
                cx = base_x + idx * opt_spacing
                pid = self.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#38bdf8", outline="", tags=(f"port_in:{node_id}:{name}",))
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
""",
"workspace/voide_ui/options.py": """from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog
from typing import Dict, Any

def prompt_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    template = simpledialog.askstring("Prompt Options", "Template (use {task}):", initialvalue=cfg.get("template", "{task}"), parent=master)
    if template is None:
        return cfg
    cfg["template"] = template
    return cfg

def llm_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    backend = simpledialog.askstring("LLM Options", "Backend (echo|openai|llama_cpp):", initialvalue=cfg.get("backend", "echo"), parent=master)
    if backend is not None:
        cfg["backend"] = backend
    model = simpledialog.askstring("LLM Options", "OpenAI model:", initialvalue=cfg.get("model", "gpt-4o-mini"), parent=master)
    if model is not None:
        cfg["model"] = model
    model_path = simpledialog.askstring("LLM Options", "llama.cpp model_path:", initialvalue=cfg.get("model_path", ""), parent=master)
    if model_path is not None:
        cfg["model_path"] = model_path
    fwd = simpledialog.askstring("LLM Options", "Forward input with response? (y/n):", initialvalue="y" if cfg.get("forward_input_with_response", False) else "n", parent=master)
    if fwd is not None:
        cfg["forward_input_with_response"] = fwd.lower().startswith("y")
    return cfg

def memory_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    mode = simpledialog.askstring("Memory Options", "Mode (read|write):", initialvalue=cfg.get("mode", "read"), parent=master)
    if mode is not None:
        cfg["mode"] = mode
    query = simpledialog.askstring("Memory Options", "Query (for read):", initialvalue=cfg.get("query", ""), parent=master)
    if query is not None:
        cfg["query"] = query
    k = simpledialog.askinteger("Memory Options", "k (for read):", initialvalue=int(cfg.get("k", 8)), parent=master, minvalue=1)
    if k is not None:
        cfg["k"] = int(k)
    return cfg

def cache_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    max_passes = simpledialog.askinteger(
        "Cache Options",
        "Max passes to retain:",
        initialvalue=int(cfg.get("max_passes", 3)),
        parent=master,
        minvalue=1,
    )
    if max_passes is not None:
        cfg["max_passes"] = int(max_passes)

    token_limit = simpledialog.askinteger(
        "Cache Options",
        "Token limit (0 for unlimited):",
        initialvalue=int(cfg.get("token_limit", 0)),
        parent=master,
        minvalue=0,
    )
    if token_limit is not None:
        cfg["token_limit"] = int(token_limit)

    clear_after = simpledialog.askinteger(
        "Cache Options",
        "Clear after N passes (0 = never):",
        initialvalue=int(cfg.get("clear_after", 0)),
        parent=master,
        minvalue=0,
    )
    if clear_after is not None:
        cfg["clear_after"] = int(clear_after)

    prepend = simpledialog.askstring(
        "Cache Options",
        "Place older packets before new ones? (y/n):",
        initialvalue="y" if cfg.get("prepend_mode", True) else "n",
        parent=master,
    )
    if prepend is not None:
        cfg["prepend_mode"] = prepend.lower().startswith("y")

    clear_on_build = simpledialog.askstring(
        "Cache Options",
        "Clear cache on workflow build? (y/n):",
        initialvalue="n" if not cfg.get("clear_on_build") else "y",
        parent=master,
    )
    if clear_on_build is not None:
        cfg["clear_on_build"] = clear_on_build.lower().startswith("y")

    enable_opt_in = simpledialog.askstring(
        "Cache Options",
        "Enable OPT IN port? (y/n):",
        initialvalue="y" if cfg.get("enable_opt_in") else "n",
        parent=master,
    )
    if enable_opt_in is not None:
        cfg["enable_opt_in"] = enable_opt_in.lower().startswith("y")
    return cfg

def log_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    path = simpledialog.askstring("Log Options", "Path to JSONL:", initialvalue=cfg.get("path", "artifacts/run.log"), parent=master)
    if path is not None:
        cfg["path"] = path
    return cfg

def divider_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    route_key = simpledialog.askstring("Divider Options", "Route key:", initialvalue=cfg.get("route_key", "route"), parent=master)
    if route_key is not None:
        cfg["route_key"] = route_key
    mapping_str = simpledialog.askstring("Divider Options", "Mapping (value:port,comma-separated):", initialvalue=cfg.get("_mapping_str", "alpha:A,beta:B"), parent=master)
    if mapping_str is not None:
        m: Dict[str, str] = {}
        for part in mapping_str.split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                m[k.strip()] = v.strip()
        cfg["mapping"] = m
        cfg["_mapping_str"] = mapping_str
    return cfg

def toolcall_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    tool = simpledialog.askstring("ToolCall Options", "Tool name:", initialvalue=cfg.get("tool", "python_eval"), parent=master)
    if tool is not None:
        cfg["tool"] = tool
    expr = simpledialog.askstring("ToolCall Options", "python_eval expr:", initialvalue=cfg.get("expr", "2+2"), parent=master)
    if expr is not None:
        cfg["args"] = {"expr": expr}
        cfg["expr"] = expr
    return cfg

def debate_options(master: tk.Misc, current: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(current or {})
    rounds = simpledialog.askinteger("Debate/Loop Options", "Rounds:", initialvalue=int(cfg.get("rounds", 2)), parent=master, minvalue=1)
    if rounds is not None:
        cfg["rounds"] = int(rounds)
    return cfg
""",
"workspace/voide_ui/chat.py": """from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

class ChatWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_send: Callable[[str], None]):
        super().__init__(master)
        self.title("VOIDE Chat")
        self.geometry("480x420")
        self.on_send = on_send

        self.out = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=18)
        self.out.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        frm = tk.Frame(self)
        frm.pack(fill=tk.X, padx=6, pady=6)
        self.entry = tk.Entry(frm)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._send)
        tk.Button(frm, text="Send", command=self._send).pack(side=tk.LEFT, padx=4)

    def _send(self, *_):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.append_user(text)
        self.on_send(text)

    def append_user(self, text: str):
        self.out.insert(tk.END, f"You: {text}\\n")
        self.out.see(tk.END)

    def append_assistant(self, text: str):
        self.out.insert(tk.END, f"Assistant: {text}\\n")
        self.out.see(tk.END)
""",
"workspace/voide_ui/app.py": """from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from voide import assemble
from voide.compiler import compile as compile_graph
from voide_ui.canvas import GraphCanvas
from voide_ui.chat import ChatWindow
from voide_ui import options as opt
from voide_ui.state import save_graph, load_graph

LABEL_TO_TYPE = {
    "LLM": "LLM",
    "Prompt": "Prompt",
    "Debate/Loop": "DebateLoop",
    "Cache": "Cache",
    "Log": "Log",
    "Memory": "Memory",
    "Divider": "Divider",
    "Tool Call": "ToolCall",
    "UI": "UI",
}

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("VOIDE")
        self.geometry("1000x640")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._node_seq = 0

        self._build_menu()
        self._build_toolbar()
        self._build_body()

        self.runner = None
        self.chat = None  # type: ignore

    # ---- UI ----
    def _build_menu(self):
        m = tk.Menu(self)
        sysm = tk.Menu(m, tearoff=False)
        sysm.add_command(label="Quit", command=self.destroy)
        m.add_cascade(label="System", menu=sysm)

        filem = tk.Menu(m, tearoff=False)
        filem.add_command(label="New", command=self._new)
        filem.add_command(label="Open...", command=self._open)
        filem.add_command(label="Save As...", command=self._save_as)
        m.add_cascade(label="File", menu=filem)

        editm = tk.Menu(m, tearoff=False)
        editm.add_command(label="Chat", command=self._open_chat)
        m.add_cascade(label="Edit", menu=editm)

        self.config(menu=m)

    def _build_toolbar(self):
        bar = tk.Frame(self, bg="#2b2d31")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        for name, cmd in [("Build", self._build), ("Play", self._run_once), ("Chat", self._open_chat)]:
            tk.Button(bar, text=name, command=cmd).pack(side=tk.LEFT, padx=4, pady=4)

    def _build_body(self):
        pal = tk.Frame(self, bg="#1e1f22", width=180)
        pal.grid(row=1, column=0, sticky="nsw")
        tk.Label(pal, text="Modules", fg="#e6e6e6", bg="#1e1f22").pack(anchor="w", padx=8, pady=6)
        self.palette = tk.Listbox(pal, height=16)
        self.palette.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        for label in ["LLM", "Prompt", "Debate/Loop", "Cache", "Log", "Memory", "Divider", "Tool Call", "UI"]:
            self.palette.insert(tk.END, label)
        self.palette.bind("<Double-Button-1>", self._create_node_from_palette)

        self.canvas = GraphCanvas(self, width=760, height=560)
        self.canvas.grid(row=1, column=1, sticky="nsew")
        self.canvas.bind("<Double-Button-1>", self._open_options_for_hit)

    # ---- actions ----
    def _new(self):
        self.canvas.delete("all")
        self.canvas.nodes.clear()
        self.canvas.edges.clear()

    def _open(self):
        p = filedialog.askopenfilename(filetypes=[("VOIDE Graph", "*.json")])
        if not p:
            return
        g, pos = load_graph(p)
        self.canvas.load_from(g, pos)

    def _save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("VOIDE Graph", "*.json")])
        if not p:
            return
        g, pos = self.canvas.to_graph()
        save_graph(p, g, pos)

    def _create_node_from_palette(self, *_):
        sel = self.palette.curselection()
        if not sel:
            return
        label = self.palette.get(sel[0])
        type_name = LABEL_TO_TYPE[label]
        self._node_seq += 1
        nid = f"n{self._node_seq}"
        self.canvas.add_node(nid, type_name, 60 + (self._node_seq % 5) * 40, 80 + (self._node_seq % 7) * 30, config={})

    def _open_options_for_hit(self, ev):
        items = self.canvas.find_overlapping(ev.x, ev.y, ev.x, ev.y)
        for it in items:
            for tag in self.canvas.gettags(it):
                if tag.startswith("node:"):
                    nid = tag.split(":", 1)[1]
                    self._open_options_for_node(nid)
                    return

    def _open_options_for_node(self, nid: str):
        nw = self.canvas.nodes[nid]
        t = nw.type_name
        if t == "Prompt":
            cfg = opt.prompt_options(self, nw.config)
        elif t == "LLM":
            cfg = opt.llm_options(self, nw.config)
        elif t == "Memory":
            cfg = opt.memory_options(self, nw.config)
        elif t == "Cache":
            cfg = opt.cache_options(self, nw.config)
        elif t == "Log":
            cfg = opt.log_options(self, nw.config)
        elif t == "Divider":
            cfg = opt.divider_options(self, nw.config)
        elif t == "ToolCall":
            cfg = opt.toolcall_options(self, nw.config)
        elif t == "DebateLoop":
            cfg = opt.debate_options(self, nw.config)
        else:
            cfg = dict(nw.config)
        nw.config = cfg

    def _ensure_chat(self):
        if self.chat is None or not self.chat.winfo_exists():
            self.chat = ChatWindow(self, self._on_chat_send)

    def _open_chat(self):
        self._ensure_chat()

    def _build(self):
        container = assemble()
        container.setdefault("ops", {})["UI"] = lambda m, c, ct: dict(m)
        g, _ = self.canvas.to_graph()
        try:
            runner = compile_graph(g, container)
        except Exception as e:
            messagebox.showerror("Build failed", str(e))
            return
        self.runner = runner
        messagebox.showinfo("Build", "Build successful.")

    def _on_chat_send(self, text: str):
        if not self.runner:
            self._build()
            if not self.runner:
                return
        payload = {"task": text, "prompt": text}
        try:
            out = self.runner.run(payload)
        except Exception as e:
            messagebox.showerror("Run failed", str(e))
            return
        completion = None
        for nid in reversed(list(out.keys())):
            val = out[nid]
            if isinstance(val, dict) and "completion" in val:
                completion = val["completion"]
                break
        if completion is None:
            completion = "<no completion>"
        self._ensure_chat()
        self.chat.append_assistant(str(completion))

    def _run_once(self):
        self._ensure_chat()
        txt = self.chat.entry.get().strip() if self.chat and self.chat.winfo_exists() else ""
        if txt:
            self.chat._send()
        else:
            self.chat.append_assistant("<no input>")

def launch():
    app = App()
    app.mainloop()
""",
"workspace/main_ui.py": """from __future__ import annotations

from voide_ui.app import launch

if __name__ == "__main__":
    launch()
""",
"workspace/tests/test_state_io.py": """from __future__ import annotations

from pathlib import Path

from voide.graph import Graph, Node, Edge
from voide_ui.state import save_graph, load_graph

def test_state_save_load(tmp_path: Path):
    g = Graph()
    g.add_node(Node(id="a", type_name="Prompt", config={"template": "Hello {task}"}))
    g.add_node(Node(id="b", type_name="LLM", config={"backend": "echo"}))
    g.add_edge(Edge("a", "prompt", "b", "prompt"))
    pos = {"a": (100, 120), "b": (260, 120)}

    p = tmp_path / "g.json"
    save_graph(str(p), g, pos)

    g2, pos2 = load_graph(str(p))
    assert set(g2.nodes.keys()) == {"a", "b"}
    assert len(g2.edges) == 1
    assert pos2["a"] == (100, 120) and pos2["b"] == (260, 120)
""",
}

for path, content in files.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print("[write]", p)

