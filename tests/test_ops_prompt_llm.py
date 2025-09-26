from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict


def load_chunk(name: str):
    path = Path("chunks") / f"{name}.py"
    spec = spec_from_file_location(f"voide_test_chunk_{name}", path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def make_container() -> Dict[str, Any]:
    return {"ops": {}, "tools": {}, "config": {}}


def register_chunk(name: str, container: Dict[str, Any]):
    module = load_chunk(name)
    module.build(container)
    return module


def test_prompt_renders():
    c = make_container()
    register_chunk("prompt", c)
    op = c["ops"]["Prompt"]
    msg = {"task": "reverse a string"}
    cfg = {"template": "Summarize {task}"}
    out = op(msg, cfg, c)
    assert out["prompt"] == "Summarize reverse a string"


def test_llm_echo_completion():
    c = make_container()
    register_chunk("llm", c)
    op = c["ops"]["LLM"]
    msg = {"prompt": "Say hi"}
    cfg = {"backend": "echo", "forward_input_with_response": True}
    out = op(msg, cfg, c)
    assert out["completion"].startswith("ECHO:")
    assert out.get("input") == msg

