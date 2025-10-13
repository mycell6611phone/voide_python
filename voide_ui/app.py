from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from typing import Any, Dict
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
        self._increase_font_sizes(15)
        self.title("VOIDE")
        self.geometry("1000x640")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._configure_fonts()
        self._font_var = tk.StringVar(value=self._default_canvas_font())
        self._node_seq = 0
        self._option_windows: dict[str, tk.Toplevel] = {}
        self._llm_settings: Dict[str, Any] | None = None

        self._build_menu()
        self._build_toolbar()
        self._build_body()

        self.runner = None
        self.chat: ChatWindow | None = None

        # Instantiate the chat window immediately so it can be toggled without
        # relying on recreation after it has been hidden.
        self._ensure_chat().show()

    # ---- UI ----
    def _configure_fonts(self) -> None:
        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
        ):
            try:
                f = tkfont.nametofont(name)
            except tk.TclError:
                continue
            f.configure(size=f.cget("size") + 5)

    def register_node(self, node_id: str) -> None:
        if node_id.startswith("n"):
            try:
                val = int(node_id[1:])
            except ValueError:
                return
            self._node_seq = max(self._node_seq, val)

    def next_node_id(self) -> str:
        self._node_seq += 1
        return f"n{self._node_seq}"

    def close_option_window(self, node_id: str) -> None:
        win = self._option_windows.pop(node_id, None)
        if win and win.winfo_exists():
            win.destroy()

    def _close_all_option_windows(self) -> None:
        for nid in list(self._option_windows.keys()):
            self.close_option_window(nid)

    def _default_canvas_font(self) -> str:
        try:
            return tkfont.nametofont("TkDefaultFont").cget("family")
        except tk.TclError:
            return "Arial"

    def _set_canvas_font(self, family: str) -> None:
        if not family:
            return
        self._font_var.set(family)
        canvas = getattr(self, "canvas", None)
        if canvas is not None and hasattr(canvas, "set_label_font_family"):
            try:
                canvas.set_label_font_family(family)
            except tk.TclError:
                pass

    def _build_menu(self):
        m = tk.Menu(self)
        sysm = tk.Menu(m, tearoff=False)
        sysm.add_command(label="Quit", command=self.destroy)
        m.add_cascade(label="System", menu=sysm)

        filem = tk.Menu(m, tearoff=False)
        filem.add_command(label="New", command=self._new)
        filem.add_command(label="Open...", command=self._open)
        filem.add_command(label="Save As...", command=self._save_as)
        fontm = tk.Menu(filem, tearoff=False)
        font_options = [
            ("Arial", "Arial"),
            ("Courier New (monospace)", "Courier New"),
            ("Helvetica", "Helvetica"),
            ("Times New Roman", "Times New Roman"),
            ("Verdana", "Verdana"),
        ]
        for label, family in font_options:
            fontm.add_radiobutton(
                label=label,
                value=family,
                variable=self._font_var,
                command=lambda fam=family: self._set_canvas_font(fam),
            )
        filem.add_cascade(label="Canvas Font", menu=fontm)
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
        self.canvas.node_click_callback = self._on_canvas_node_click

        self._set_canvas_font(self._font_var.get())


    # ---- actions ----
    def _new(self):
        self._close_all_option_windows()
        self.canvas.delete("all")
        self.canvas.nodes.clear()
        self.canvas.edges.clear()
        self._node_seq = 0

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
        nid = self.next_node_id()
        self.canvas.add_node(nid, type_name, 60 + (self._node_seq % 5) * 40, 80 + (self._node_seq % 7) * 30, config={})

    def _open_options_for_hit(self, ev):
        items = self.canvas.find_overlapping(ev.x, ev.y, ev.x, ev.y)
        for it in items:
            for tag in self.canvas.gettags(it):
                if tag.startswith("node:"):
                    nid = tag.split(":", 1)[1]
                    self._open_options_for_node(nid)
                    return

    def _on_node_click(self, event):
        nid = getattr(event, "data", None)
        if not nid:
            return
        if nid not in self.canvas.nodes:
            return
        self._open_options_for_node(nid)

    def _open_options_for_node(self, nid: str):
        nw = self.canvas.nodes[nid]
        t = nw.type_name
        if t == "UI":
            self._open_chat()
            return
        existing = self._option_windows.get(nid)
        if existing and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return

        def on_apply(cfg: dict):
            nw.config = cfg

        def on_close() -> None:
            self._option_windows.pop(nid, None)

        win = opt.open_module_options(self, nid, t, dict(nw.config), on_apply, on_close)
        self._option_windows[nid] = win

    def _ensure_chat(self) -> ChatWindow:
        chat = self.chat
        exists = False
        if chat is not None:
            try:
                exists = bool(chat.winfo_exists())
            except tk.TclError:
                exists = False
        if not exists:
            chat = ChatWindow(self, self._on_chat_send)
            self.chat = chat
        return chat

    def _open_chat(self):
        chat = self._ensure_chat()
        chat.show()

    def _toggle_chat(self):
        chat = self._ensure_chat()
        chat.toggle()

    def _on_canvas_node_click(self, node_id: str, node_widget):
        if getattr(node_widget, "type_name", None) == "UI":
            self._toggle_chat()

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
        chat = self._ensure_chat()
        chat.show()
        chat.append_assistant(str(completion))

    def _run_once(self):
        chat = self._ensure_chat()
        chat.show()
        txt = chat.entry.get().strip() if chat.winfo_exists() else ""
        if txt:
            chat._send()
        else:
            chat.append_assistant("<no input>")

    def _increase_font_sizes(self, delta: int) -> None:
        font_names = (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
            "TkTooltipFont",
        )
        for name in font_names:
            try:
                font = tkfont.nametofont(name)
            except tk.TclError:
                continue
            size = font.cget("size")
            try:
                size_val = int(size)
            except (TypeError, ValueError):
                continue
            if size_val < 0:
                font.configure(size=size_val - delta)
            else:
                font.configure(size=size_val + delta)

    def on_llm_settings_changed(self, config: Dict[str, Any]) -> None:
        self._llm_settings = dict(config)

def launch():
    app = App()
    app.mainloop()
