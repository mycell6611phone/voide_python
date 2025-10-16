from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


LLAMA_ADAPTER_NAME = "llama.cpp"


class EnvFile:
    """Minimal .env parser/persistor that preserves unrelated entries."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lines: List[str] = []
        self._key_to_index: Dict[str, int] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._lines = []
            self._key_to_index = {}
            return

        self._lines = text.splitlines()
        self._key_to_index.clear()
        for idx, line in enumerate(self._lines):
            key = self._extract_key(line)
            if key is not None and key not in self._key_to_index:
                self._key_to_index[key] = idx

    @staticmethod
    def _extract_key(line: str) -> str | None:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None
        if "=" not in stripped:
            return None
        return stripped.split("=", 1)[0].strip()

    def get(self, key: str) -> str | None:
        idx = self._key_to_index.get(key)
        if idx is None:
            return None
        line = self._lines[idx]
        if "=" not in line:
            return None
        return line.split("=", 1)[1]

    def set(self, key: str, value: str) -> bool:
        new_line = f"{key}={value}"
        idx = self._key_to_index.get(key)
        if idx is not None:
            if self._lines[idx] == new_line:
                return False
            self._lines[idx] = new_line
        else:
            self._lines.append(new_line)
            self._key_to_index[key] = len(self._lines) - 1
        self._dirty = True
        return True

    def write(self) -> bool:
        if not self._dirty:
            return False
        text = "\n".join(self._lines)
        if self._lines:
            text += "\n"
        self.path.write_text(text, encoding="utf-8")
        self._dirty = False
        return True


def load_llm_config(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return dict(data) if isinstance(data, dict) else {}


def save_llm_config(path: Path, config: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config, indent=2)
    path.write_text(payload + "\n", encoding="utf-8")


def _collect_entries(raw: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(raw, dict):
        models = raw.get("models")
        if isinstance(models, list):
            for item in models:
                if isinstance(item, dict):
                    yield item
            return
        yielded = False
        for value in raw.values():
            if isinstance(value, dict):
                yielded = True
                yield value
        if not yielded and "adapter" in raw:
            yield raw


def load_llama_models_from_file(path: Path) -> List[Dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return []

    models: List[Dict[str, Any]] = []
    for entry in _collect_entries(raw):
        adapter = entry.get("adapter")
        if adapter is None:
            filename = entry.get("filename")
            if isinstance(filename, str) and filename.lower().endswith(".gguf"):
                adapter = LLAMA_ADAPTER_NAME
        if adapter != LLAMA_ADAPTER_NAME:
            continue
        normalized = dict(entry)
        name = normalized.get("name") or normalized.get("filename") or "Unnamed model"
        normalized["name"] = str(name)
        if "filename" in normalized and normalized["filename"] is not None:
            normalized["filename"] = str(normalized["filename"])
        models.append(normalized)
    return models


def resolve_llama_model_file(models_json_path: Path, entry: Mapping[str, Any]) -> Path:
    filename = entry.get("filename")
    if not filename:
        raise ValueError("Model entry is missing a filename")
    base = models_json_path.expanduser().parent
    return base / str(filename)


__all__ = [
    "EnvFile",
    "LLAMA_ADAPTER_NAME",
    "load_llm_config",
    "save_llm_config",
    "load_llama_models_from_file",
    "resolve_llama_model_file",
]

