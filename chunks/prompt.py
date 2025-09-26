"""Prompt chunk: registers the Prompt op."""

from __future__ import annotations

from typing import Any, Dict

provides = ["ops"]
requires: list[str] = []


def _render(template: str, message: Dict[str, Any]) -> str:
    """Minimal replacement of the ``{task}`` placeholder."""

    return template.replace("{task}", str(message.get("task", "")))


def op_prompt(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
    template = config.get("template", "{task}")
    return {"prompt": _render(template, message)}


def build(container: Dict[str, Any]) -> None:
    container.setdefault("ops", {})["Prompt"] = op_prompt
