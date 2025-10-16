from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Dict, List, Tuple

from voide_ui.llm_settings import load_llama_models_from_file, resolve_llama_model_file

BG_COLOR = "#2b2d31"
FG_COLOR = "#f5f5f5"
LABEL_COLOR = "#e6e6e6"
ENTRY_BG = "#3b3d44"

DEFAULT_OPENAI_MODELS: List[str] = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4.1-nano",
    "gpt-3.5-turbo",
]

BACKEND_ORDER: Tuple[str, ...] = ("echo", "openai", "llama_cpp", "gpt4all")
BACKEND_LABELS: Dict[str, str] = {
    "echo": "Echo (debug)",
    "openai": "OpenAI",
    "llama_cpp": "llama.cpp",
    "gpt4all": "GPT4All",
}
LABEL_TO_BACKEND: Dict[str, str] = {label: backend for backend, label in BACKEND_LABELS.items()}

MODELS_JSON_PATH = Path(__file__).resolve().parents[1] / "models" / "models.json"


def _load_model_catalog() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    llama: List[Tuple[str, str]] = []
    gpt4all: List[Tuple[str, str]] = []
    try:
        entries = load_llama_models_from_file(MODELS_JSON_PATH)
    except Exception:
        return llama, gpt4all

    for entry in entries:
        try:
            resolved = resolve_llama_model_file(MODELS_JSON_PATH, entry)
        except Exception:
            continue
        name = str(entry.get("name") or resolved.name)
        short = resolved.name
        label = f"{name} ({short})" if name != short else name
        url = str(entry.get("url", "")).lower()
        target = gpt4all if "gpt4all" in url or "gpt4all" in name.lower() else llama
        target.append((label, str(resolved)))

    return llama, gpt4all


LLAMA_MODEL_CHOICES, GPT4ALL_MODEL_CHOICES = _load_model_catalog()


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
    def _label(self, text: str, parent: tk.Misc | None = None) -> None:
        target = parent or self.body
        tk.Label(target, text=text, anchor="w", bg=BG_COLOR, fg=LABEL_COLOR).pack(fill=tk.X, pady=(0, 4))

    def _entry(self, var: tk.Variable, parent: tk.Misc | None = None, **kw) -> tk.Entry:
        target = parent or self.body
        ent = tk.Entry(target, textvariable=var, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR, **kw)
        ent.pack(fill=tk.X, pady=(0, 12))
        return ent

    def _spinbox(self, var: tk.Variable, from_: int, to: int, parent: tk.Misc | None = None, **kw) -> tk.Spinbox:
        target = parent or self.body
        sp = tk.Spinbox(
            target,
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

    def _text(self, initial: str, height: int = 6, parent: tk.Misc | None = None) -> tk.Text:
        target = parent or self.body
        txt = tk.Text(target, wrap=tk.WORD, height=height, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR)
        txt.insert("1.0", initial)
        txt.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        return txt

    def _option_menu(
        self,
        var: tk.StringVar,
        values: List[str],
        parent: tk.Misc | None = None,
        command: Callable[[str], None] | None = None,
    ) -> tk.OptionMenu:
        target = parent or self.body
        opts = values or ["<none>"]
        menu = tk.OptionMenu(target, var, *opts, command=command)
        menu.configure(bg=ENTRY_BG, fg=FG_COLOR, activebackground=ENTRY_BG, activeforeground=FG_COLOR, highlightthickness=0)
        menu["menu"].configure(bg=ENTRY_BG, fg=FG_COLOR, activebackground=BG_COLOR, activeforeground=FG_COLOR)
        menu.pack(fill=tk.X, pady=(0, 12))
        return menu

    def _path_entry(
        self,
        var: tk.StringVar,
        parent: tk.Misc,
        *,
        directory: bool = False,
        filetypes: Tuple[Tuple[str, str], ...] | None = None,
    ) -> tk.Entry:
        frame = tk.Frame(parent, bg=BG_COLOR)
        frame.pack(fill=tk.X, pady=(0, 12))
        entry = tk.Entry(frame, textvariable=var, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def _browse() -> None:
            if directory:
                path = filedialog.askdirectory()
            else:
                ft = filetypes or (("Model files", "*.gguf"), ("All files", "*.*"))
                path = filedialog.askopenfilename(filetypes=ft)
            if path:
                var.set(str(Path(path).expanduser()))

        tk.Button(frame, text="Browse", command=_browse).pack(side=tk.RIGHT, padx=(8, 0))
        return entry

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
        backend_value = self._normalize_backend(self._config.get("backend"))
        openai_model = self._config.get("model") or DEFAULT_OPENAI_MODELS[0]

        self.backend = tk.StringVar(value=backend_value)
        self.backend_label = tk.StringVar(value=BACKEND_LABELS.get(backend_value, backend_value))
        self.openai_model = tk.StringVar(value=openai_model if openai_model else DEFAULT_OPENAI_MODELS[0])
        self.openai_api_key = tk.StringVar(value=self._config.get("openai_api_key", ""))
        self.model_path = tk.StringVar(value=self._config.get("model_path", ""))
        self.llama_cpp_dir = tk.StringVar(value=self._config.get("llama_cpp_dir", ""))
        self.gpt4all_dir = tk.StringVar(value=self._config.get("gpt4all_dir", ""))
        self.model_choice = tk.StringVar(value="")
        self.forward_input = tk.BooleanVar(value=self._config.get("forward_input_with_response", False))
        self._current_model_map: Dict[str, str] = {}

        backend_labels = [BACKEND_LABELS[b] for b in BACKEND_ORDER]
        if self.backend_label.get() not in backend_labels:
            backend_labels.insert(0, self.backend_label.get())

        self._label("Backend")
        self._option_menu(
            self.backend_label,
            backend_labels,
            command=self._on_backend_label_change,
        )

        self.dynamic_frame = tk.Frame(self.body, bg=BG_COLOR)
        self.dynamic_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self.backend.trace_add("write", self._on_backend_change)
        self._render_backend_options()

        tk.Checkbutton(
            self.body,
            text="Forward input with response",
            variable=self.forward_input,
            bg=BG_COLOR,
            fg=LABEL_COLOR,
            selectcolor=BG_COLOR,
            activebackground=BG_COLOR,
            activeforeground=LABEL_COLOR,
        ).pack(anchor="w", pady=(0, 12))

    def _normalize_backend(self, raw: str | None) -> str:
        if not raw:
            return "echo"
        value = str(raw).strip()
        lowered = value.lower()
        if lowered in {"llama.cpp", "llama_cpp"}:
            return "llama_cpp"
        for backend in BACKEND_ORDER:
            if lowered == backend:
                return backend
            if lowered == backend.replace("_", "."):
                return backend
        return value

    def _on_backend_label_change(self, selection: str) -> None:
        backend = LABEL_TO_BACKEND.get(selection, "echo")
        self.backend.set(backend)

    def _on_backend_change(self, *_args) -> None:
        backend = self._normalize_backend(self.backend.get())
        if backend != self.backend.get():
            self.backend.set(backend)
            return
        label = BACKEND_LABELS.get(backend, backend)
        if self.backend_label.get() != label:
            self.backend_label.set(label)
        self._render_backend_options()

    def _render_backend_options(self) -> None:
        for child in self.dynamic_frame.winfo_children():
            child.destroy()
        backend = self._normalize_backend(self.backend.get())
        if backend == "openai":
            self._build_openai_options(self.dynamic_frame)
        elif backend == "llama_cpp":
            self._build_llama_options(self.dynamic_frame)
        elif backend == "gpt4all":
            self._build_gpt4all_options(self.dynamic_frame)
        else:
            self._build_echo_options(self.dynamic_frame)

    def _build_openai_options(self, parent: tk.Misc) -> None:
        self._current_model_map = {}
        models = list(DEFAULT_OPENAI_MODELS)
        current = self.openai_model.get().strip()
        if current and current not in models:
            models.insert(0, current)
        self._label("OpenAI API key", parent)
        self._entry(self.openai_api_key, parent, show="*")
        self._label("Model", parent)
        self._option_menu(self.openai_model, models, parent)

    def _build_llama_options(self, parent: tk.Misc) -> None:
        self._label("llama.cpp directory", parent)
        self._path_entry(self.llama_cpp_dir, parent, directory=True)
        self._label("Model selection", parent)
        self._build_model_selector(parent, LLAMA_MODEL_CHOICES)
        self._label("Model file path", parent)
        self._path_entry(self.model_path, parent)

    def _build_gpt4all_options(self, parent: tk.Misc) -> None:
        self._label("GPT4All models directory", parent)
        self._path_entry(self.gpt4all_dir, parent, directory=True)
        self._label("Model selection", parent)
        self._build_model_selector(parent, GPT4ALL_MODEL_CHOICES)
        self._label("Model file path", parent)
        self._path_entry(self.model_path, parent)

    def _build_echo_options(self, parent: tk.Misc) -> None:
        self._current_model_map = {}
        self._label("No additional options for the echo backend.", parent)

    def _build_model_selector(self, parent: tk.Misc, catalog: List[Tuple[str, str]]) -> None:
        mapping = {label: path for label, path in catalog}
        self._current_model_map = mapping
        if not catalog:
            self._label("No catalog entries found. Use Browse to select a model file.", parent)
            return

        current_path = Path(self.model_path.get().strip()).expanduser() if self.model_path.get().strip() else None
        selection = None
        if current_path:
            for label, path in catalog:
                if Path(path).expanduser() == current_path:
                    selection = label
                    break

        choices = [label for label, _ in catalog]
        if selection is None:
            if self.model_path.get().strip():
                selection = "Custom path"
                if "Custom path" not in choices:
                    choices.append("Custom path")
            else:
                first_label, first_path = catalog[0]
                selection = first_label
                self.model_path.set(first_path)
        self.model_choice.set(selection)
        self._option_menu(
            self.model_choice,
            choices,
            parent,
            command=lambda choice: self._on_model_choice(choice),
        )

    def _on_model_choice(self, selection: str) -> None:
        path = self._current_model_map.get(selection)
        if path:
            self.model_path.set(path)

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        backend = self._normalize_backend(self.backend.get())

        for key in ("model", "model_path", "openai_api_key", "llama_cpp_dir", "gpt4all_dir"):
            cfg.pop(key, None)

        cfg["backend"] = backend
        cfg["forward_input_with_response"] = bool(self.forward_input.get())

        if backend == "openai":
            model = self.openai_model.get().strip() or DEFAULT_OPENAI_MODELS[0]
            cfg["model"] = model
            key = self.openai_api_key.get().strip()
            if key:
                cfg["openai_api_key"] = key
        elif backend == "llama_cpp":
            path = self.model_path.get().strip()
            if path:
                cfg["model_path"] = path
                cfg["model"] = Path(path).stem
            directory = self.llama_cpp_dir.get().strip()
            if directory:
                cfg["llama_cpp_dir"] = directory
        elif backend == "gpt4all":
            path = self.model_path.get().strip()
            if path:
                cfg["model_path"] = path
                cfg["model"] = Path(path).stem
            directory = self.gpt4all_dir.get().strip()
            if directory:
                cfg["gpt4all_dir"] = directory
        else:
            path = self.model_path.get().strip()
            if path:
                cfg["model_path"] = path

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
        self.max_passes = tk.IntVar(value=int(self._config.get("max_passes", 3)))
        self.token_limit = tk.IntVar(value=int(self._config.get("token_limit", 0)))
        self.clear_after = tk.IntVar(value=int(self._config.get("clear_after", 0)))
        self.prepend_mode = tk.BooleanVar(value=bool(self._config.get("prepend_mode", True)))
        self.clear_on_build = tk.BooleanVar(value=bool(self._config.get("clear_on_build", False)))
        self.enable_opt_in = tk.BooleanVar(value=bool(self._config.get("enable_opt_in", False)))

        self._label("Max passes to retain")
        self._spinbox(self.max_passes, from_=1, to=100, increment=1)
        self._label("Token limit (0 = unlimited)")
        self._spinbox(self.token_limit, from_=0, to=100000, increment=50)
        self._label("Clear after N passes (0 = never)")
        self._spinbox(self.clear_after, from_=0, to=100, increment=1)

        tk.Checkbutton(
            self.body,
            text="Place older packets before new ones",
            variable=self.prepend_mode,
            bg=BG_COLOR,
            fg=LABEL_COLOR,
            selectcolor=BG_COLOR,
            activebackground=BG_COLOR,
            activeforeground=LABEL_COLOR,
        ).pack(anchor="w", pady=(0, 8))

        tk.Checkbutton(
            self.body,
            text="Clear cache when workflow builds",
            variable=self.clear_on_build,
            bg=BG_COLOR,
            fg=LABEL_COLOR,
            selectcolor=BG_COLOR,
            activebackground=BG_COLOR,
            activeforeground=LABEL_COLOR,
        ).pack(anchor="w", pady=(0, 8))

        tk.Checkbutton(
            self.body,
            text="Enable OPT IN port",
            variable=self.enable_opt_in,
            bg=BG_COLOR,
            fg=LABEL_COLOR,
            selectcolor=BG_COLOR,
            activebackground=BG_COLOR,
            activeforeground=LABEL_COLOR,
        ).pack(anchor="w", pady=(0, 12))

    def _collect(self) -> Dict:
        cfg = dict(self._config)
        try:
            cfg["max_passes"] = max(1, int(self.max_passes.get()))
        except (TypeError, ValueError):
            cfg["max_passes"] = 1
        try:
            cfg["token_limit"] = max(0, int(self.token_limit.get()))
        except (TypeError, ValueError):
            cfg["token_limit"] = 0
        try:
            cfg["clear_after"] = max(0, int(self.clear_after.get()))
        except (TypeError, ValueError):
            cfg["clear_after"] = 0
        cfg["prepend_mode"] = bool(self.prepend_mode.get())
        cfg["clear_on_build"] = bool(self.clear_on_build.get())
        cfg["enable_opt_in"] = bool(self.enable_opt_in.get())
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
