from __future__ import annotations

import json
from pathlib import Path

from voide_ui.llm_settings import (
    EnvFile,
    load_llm_config,
    load_llama_models_from_file,
    resolve_llama_model_file,
    save_llm_config,
)


def test_load_llm_config_round_trip(tmp_path):
    path = tmp_path / "llm.config.json"
    data = {"backend": "openai", "forward_input_with_response": True}
    save_llm_config(path, data)
    loaded = load_llm_config(path)
    assert loaded == data


def test_load_llm_config_missing_returns_empty(tmp_path):
    missing = tmp_path / "missing.json"
    assert load_llm_config(missing) == {}


def test_env_file_preserves_existing_lines(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("FOO=bar\n# comment\n", encoding="utf-8")

    env = EnvFile(env_path)
    assert env.get("FOO") == "bar"
    assert env.set("FOO", "bar") is False
    assert env.set("FOO", "baz") is True
    assert env.set("NEW", "value") is True
    env.write()

    contents = env_path.read_text(encoding="utf-8")
    assert "FOO=baz" in contents
    assert "NEW=value" in contents
    assert "# comment" in contents


def test_load_llama_models_from_file_filters_by_adapter(tmp_path):
    models_path = tmp_path / "models.json"
    payload = [
        {"name": "Keep", "filename": "keep.gguf", "adapter": "llama.cpp", "quant": "q4"},
        {"name": "Skip", "filename": "skip.gguf", "adapter": "other"},
    ]
    models_path.write_text(json.dumps(payload), encoding="utf-8")

    models = load_llama_models_from_file(models_path)
    assert [m["name"] for m in models] == ["Keep"]
    assert models[0]["filename"] == "keep.gguf"


def test_load_llama_models_from_nested_structure(tmp_path):
    models_path = tmp_path / "models.json"
    payload = {"models": [{"filename": "nested.gguf", "adapter": "llama.cpp"}]}
    models_path.write_text(json.dumps(payload), encoding="utf-8")

    models = load_llama_models_from_file(models_path)
    assert models and models[0]["name"] == "nested.gguf"


def test_resolve_llama_model_file(tmp_path):
    models_path = tmp_path / "models.json"
    models_path.write_text("[]", encoding="utf-8")

    entry = {"filename": "model.gguf"}
    resolved = resolve_llama_model_file(models_path, entry)
    assert resolved == Path(models_path.parent, "model.gguf")
