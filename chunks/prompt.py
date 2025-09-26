# File: workspace/chunks/prompt.py
"""Prompt chunk: registers the Prompt op."""
from __future__ import annotations
from typing import Any, Dict


provides = ["ops"]
requires: list[str] = []


def _render(template: str, message: Dict[str, Any]) -> str:
<<<<<<< ours
    """Minimal replacement of the ``{task}`` placeholder."""
=======
    # Minimal replacement: {task}
    return template.replace("{task}", str(message.get("task", "")))
>>>>>>> theirs

    return template.replace("{task}", str(message.get("task", "")))

<<<<<<< ours

def op_prompt(
    message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]
) -> Dict[str, Any]:
=======
def op_prompt(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
>>>>>>> theirs
    template = config.get("template", "{task}")
    return {"prompt": _render(template, message)}


def build(container: Dict[str, Any]) -> None:
    container.setdefault("ops", {})["Prompt"] = op_prompt
