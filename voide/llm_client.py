# File: workspace/voide/llm_client.py
)
return resp.choices[0].message.content or ""


@dataclass
class LLMConfig:
backend: str = "echo"
model_path: str | None = None
model: str | None = None
max_input_tokens: int | None = 4096
max_response_tokens: int | None = 512
forward_input_with_response: bool = False


class LLMClient:
"""Facade selecting a backend with graceful fallback to echo."""


def __init__(self, config: Dict[str, Any] | None = None, *, fallback_to_echo: bool = True) -> None:
cfg = LLMConfig(**(config or {}))
self.config = cfg
self.backend = cfg.backend
try:
if cfg.backend == "llama_cpp":
if not cfg.model_path:
raise FileNotFoundError("model_path required for llama_cpp")
self._adapter = LlamaCppAdapter(cfg.model_path)
elif cfg.backend == "openai":
self._adapter = OpenAIAdapter(model=(cfg.model or "gpt-4o-mini"))
else:
self._adapter = EchoAdapter()
self.backend = "echo"
except Exception:
if not fallback_to_echo:
raise
self._adapter = EchoAdapter()
self.backend = "echo"


def complete(self, prompt: str) -> str:
return self._adapter.complete(prompt, self.config.max_response_tokens)


def chat(self, messages: List[Dict[str, str]]) -> str:
return self._adapter.chat(messages, self.config.max_response_tokens)
