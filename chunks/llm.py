# File: workspace/chunks/llm.py
"""LLM chunk: registers LLM op and default client."""
from __future__ import annotations
from typing import Any, Dict, List


from voide.llm_client import LLMClient


provides = ["ops", "llm_client"]
requires: list[str] = []


def op_llm(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
client: LLMClient | None = container.get("llm_client") if not config else None
if client is None:
client = LLMClient(config or {})
fwd = bool((config or {}).get("forward_input_with_response", getattr(client.config, "forward_input_with_response")))
if "messages" in message:
text = client.chat(message["messages"])
elif "prompt" in message:
text = client.complete(str(message["prompt"]))
else:
text = client.complete(str(message))
out: Dict[str, Any] = {"completion": text}
if fwd:
out["input"] = message
return out


def build(container: Dict[str, Any]) -> None:
container.setdefault("ops", {})["LLM"] = op_llm
container["llm_client"] = LLMClient({"backend": "echo"})
