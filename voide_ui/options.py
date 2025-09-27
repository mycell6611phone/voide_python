from __future__ import annotations

import json
import tkinter as tk
from typing import Callable, Dict

BG_COLOR = "#2b2d31"
FG_COLOR = "#f5f5f5"
LABEL_COLOR = "#e6e6e6"
ENTRY_BG = "#3b3d44"


class ModuleOptionsWindow(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        node_id: str,
        title: str,
        initial: Dict,
        on_apply: Callable[[Dict], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.node_id = node_id
        self._config = dict(initial)
        self._on_apply_cb = on_apply
        self._on_close_cb = on_close
        self._closed = False

        self.title(f"{title} Options")
        self.configure(bg=BG_COLOR)
        self.transient(master)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)
        self.bind("<Escape>", lambda _e: self._handle_cancel())

        self.body = tk.Frame(self, bg=BG_COLOR)
        self.body.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        self._build_body()

        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 16))
        tk.Button(btn_frame, text="Save", command=self._handle_save).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_frame, text="Cancel", command=self._handle_cancel).pack(side=tk.RIGHT)

    # -- helpers --
    def _label(self, text: str) -> None:
        tk.Label(self.body, text=text, anchor="w", bg=BG_COLOR, fg=LABEL_COLOR).pack(fill=tk.X, pady=(0, 4))

    def _entry(self, var: tk.Variable, **kw) -> tk.Entry:
        ent = tk.Entry(self.body, textvariable=var, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, **kw)
        ent.pack(fill=tk.X, pady=(0, 12))
        return ent

    def _spinbox(self, var: tk.Variable, from_: int, to: int, **kw) -> tk.Spinbox:
        sp = tk.Spinbox(
            self.body,
            textvariable=var,
            from_=from_,
            to=to,
            bg=ENTRY_BG,
            fg=FG_COLOR,
            insertbackground=FG_COLOR,
            buttonbackground=BG_COLOR,
            **kw,
        )
        sp.pack(fill=tk.X, pady=(0, 12))
        return sp

    def _text(self, initial: str, height: int = 6) -> tk.Text:
        txt = tk.Text(self.body, wrap=tk.WORD, height=height, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR)
        txt.insert("1.0", initial)
        txt.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        return txt

    def _build_body(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _collect(self) -> Dict:  # pragma: no cover - abstract
        raise NotImplementedError

    def _handle_save(self) -> None:
        cfg = self._collect()
        self._on_apply_cb(cfg)
        self.destroy()

    def _handle_cancel(self) -> None:
        self.destroy()

    def destroy(self) -> None:  # noqa: D401
        """Ensure the close callback fires once when the window is destroyed."""

        if not self._closed:
            self._closed = True
            self._on_close_cb()
        super().destroy()


class PromptOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self._label("Prompt Template")
        initial = self._config.get("template", "{task}")
        self.template = self._text(initial, height=8)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        text = self.template.get("1.0", tk.END).strip()
        cfg["template"] = text or "{task}"
        return cfg


class LLMOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.backend = tk.StringVar(value=self._config.get("backend", "echo"))
        self.model = tk.StringVar(value=self._config.get("model", "gpt-4o-mini"))
        self.model_path = tk.StringVar(value=self._config.get("model_path", ""))
        self.forward_input = tk.BooleanVar(value=self._config.get("forward_input_with_response", False))

        self._label("Backend (echo|openai|llama_cpp)")
        self._entry(self.backend)
        self._label("OpenAI Model")
        self._entry(self.model)
        self._label("llama.cpp model_path")
        self._entry(self.model_path)
        chk = tk.Checkbutton(
            self.body,
            text="Forward input with response",
            variable=self.forward_input,
            bg=BG_COLOR,
            fg=LABEL_COLOR,
            selectcolor=BG_COLOR,
            activebackground=BG_COLOR,
            activeforeground=LABEL_COLOR,
        )
        chk.pack(anchor="w", pady=(0, 12))

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        cfg["backend"] = self.backend.get().strip() or "echo"
        cfg["model"] = self.model.get().strip() or "gpt-4o-mini"
        cfg["model_path"] = self.model_path.get().strip()
        cfg["forward_input_with_response"] = bool(self.forward_input.get())
        return cfg


class MemoryOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.mode = tk.StringVar(value=self._config.get("mode", "read"))
        self.query = tk.StringVar(value=self._config.get("query", ""))
        self.k = tk.IntVar(value=int(self._config.get("k", 8)))

        self._label("Mode (read|write)")
        self._entry(self.mode)
        self._label("Query")
        self._entry(self.query)
        self._label("k (results)")
        self._spinbox(self.k, from_=1, to=100)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        cfg["mode"] = self.mode.get().strip() or "read"
        cfg["query"] = self.query.get().strip()
        try:
            cfg["k"] = max(1, int(self.k.get()))
        except (TypeError, ValueError):
            cfg["k"] = 1
        return cfg


class CacheOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.strategy = tk.StringVar(value=self._config.get("strategy", "prefer"))
        self.ttl = tk.IntVar(value=int(self._config.get("ttl_seconds", 300)))

        self._label("Strategy (off|prefer|refresh)")
        self._entry(self.strategy)
        self._label("TTL seconds")
        self._spinbox(self.ttl, from_=0, to=86400, increment=30)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        cfg["strategy"] = self.strategy.get().strip() or "prefer"
        try:
            cfg["ttl_seconds"] = max(0, int(self.ttl.get()))
        except (TypeError, ValueError):
            cfg["ttl_seconds"] = 0
        return cfg


class LogOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.path = tk.StringVar(value=self._config.get("path", "artifacts/run.log"))
        self._label("Path to JSONL log")
        self._entry(self.path)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        cfg["path"] = self.path.get().strip() or "artifacts/run.log"
        return cfg


class DividerOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.route_key = tk.StringVar(value=self._config.get("route_key", "route"))
        mapping = self._config.get("mapping", {})
        if isinstance(mapping, dict):
            mapping_str = ",".join(f"{k}:{v}" for k, v in mapping.items())
        else:
            mapping_str = str(mapping)
        self.mapping = tk.StringVar(value=self._config.get("_mapping_str", mapping_str or "alpha:A,beta:B"))

        self._label("Route key")
        self._entry(self.route_key)
        self._label("Mapping (value:port, comma separated)")
        self._entry(self.mapping)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        cfg["route_key"] = self.route_key.get().strip() or "route"
        mapping_str = self.mapping.get().strip()
        mapping: Dict[str, str] = {}
        if mapping_str:
            for part in mapping_str.split(","):
                if ":" in part:
                    k, v = part.split(":", 1)
                    mapping[k.strip()] = v.strip()
        cfg["mapping"] = mapping
        cfg["_mapping_str"] = mapping_str
        return cfg


class ToolCallOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.tool = tk.StringVar(value=self._config.get("tool", "python_eval"))
        expr = ""
        if "expr" in self._config:
            expr = str(self._config.get("expr", ""))
        elif "args" in self._config and isinstance(self._config["args"], dict):
            expr = str(self._config["args"].get("expr", ""))
        self.expr = tk.StringVar(value=expr or "2+2")

        self._label("Tool name")
        self._entry(self.tool)
        self._label("python_eval expression")
        self._entry(self.expr)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        cfg["tool"] = self.tool.get().strip() or "python_eval"
        expression = self.expr.get().strip() or "2+2"
        cfg["expr"] = expression
        cfg["args"] = {"expr": expression}
        return cfg


class DebateOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        self.rounds = tk.IntVar(value=int(self._config.get("rounds", 2)))
        self._label("Rounds")
        self._spinbox(self.rounds, from_=1, to=20)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        try:
            cfg["rounds"] = max(1, int(self.rounds.get()))
        except (TypeError, ValueError):
            cfg["rounds"] = 1
        return cfg


class GenericOptionsWindow(ModuleOptionsWindow):
    def _build_body(self) -> None:
        pretty = json.dumps(self._config, indent=2)
        self._label("Configuration (JSON)")
        self.txt = self._text(pretty, height=10)

    def _collect(self) -> Dict:
        raw = self.txt.get("1.0", tk.END).strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return dict(self._config)


WINDOWS = {
    "Prompt": PromptOptionsWindow,
    "LLM": LLMOptionsWindow,
    "Memory": MemoryOptionsWindow,
    "Cache": CacheOptionsWindow,
    "Log": LogOptionsWindow,
    "Divider": DividerOptionsWindow,
    "ToolCall": ToolCallOptionsWindow,
    "DebateLoop": DebateOptionsWindow,
}


def open_module_options(
    master: tk.Misc,
    node_id: str,
    type_name: str,
    initial: Dict,
    on_apply: Callable[[Dict], None],
    on_close: Callable[[], None],
) -> ModuleOptionsWindow:
    cls = WINDOWS.get(type_name, GenericOptionsWindow)
    return cls(master, node_id, type_name, initial, on_apply, on_close)


__all__ = ["open_module_options", "ModuleOptionsWindow"]
