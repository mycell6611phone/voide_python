from __future__ import annotations

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
