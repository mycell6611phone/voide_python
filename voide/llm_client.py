"""LLM client abstractions and lightweight fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


class Adapter(Protocol):
    """Protocol implemented by backend adapters."""

    def complete(self, prompt: str, max_tokens: int | None = None) -> str:  # pragma: no cover - protocol
        ...

    def chat(self, messages: List[Dict[str, str]], max_tokens: int | None = None) -> str:  # pragma: no cover - protocol
        ...


class EchoAdapter:
    """Fallback adapter that simply echoes the prompt back."""

    def complete(self, prompt: str, max_tokens: int | None = None) -> str:
        return f"ECHO: {prompt}"

    def chat(self, messages: List[Dict[str, str]], max_tokens: int | None = None) -> str:
        if not messages:
            return "ECHO:"
        return f"ECHO: {messages[-1].get('content', '')}"


def _extract_openai_text(response: Any) -> str:
    """Best-effort extraction of text from various OpenAI response shapes."""

    if response is None:
        return ""

    if hasattr(response, "output_text"):
        text = getattr(response, "output_text")
        if isinstance(text, str):
            return text

    if isinstance(response, dict):
        choices = response.get("choices") or []
        if choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        parts = [item.get("text") for item in content if isinstance(item, dict) and item.get("text")]
                        if parts:
                            return "".join(str(part) for part in parts)
                if isinstance(first.get("text"), str):
                    return str(first["text"])
            if isinstance(first, str):
                return first

    return str(response)


class OpenAIAdapter:
    """Very small shim around the OpenAI client.

    The adapter intentionally raises if the OpenAI SDK is unavailable so that callers
    can gracefully fall back to the echo adapter during tests.
    """

    def __init__(self, model: str, client: Any | None = None) -> None:
        if client is None:
            try:
                import openai  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("openai package is required for the OpenAI backend") from exc
            if hasattr(openai, "OpenAI"):
                client = openai.OpenAI()
            else:
                client = openai
        self._client = client
        self._model = model

    def complete(self, prompt: str, max_tokens: int | None = None) -> str:
        params: Dict[str, Any] = {"model": self._model}
        if max_tokens is not None:
            params["max_output_tokens"] = max_tokens

        if hasattr(self._client, "responses"):
            resp = self._client.responses.create(input=prompt, **params)
            return _extract_openai_text(resp)

        legacy_params = {"model": self._model, "prompt": prompt}
        if max_tokens is not None:
            legacy_params["max_tokens"] = max_tokens
        if hasattr(self._client, "Completion"):
            resp = self._client.Completion.create(**legacy_params)
            return _extract_openai_text(resp)

        raise RuntimeError("OpenAI client does not expose a supported completion API")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int | None = None) -> str:
        params: Dict[str, Any] = {"model": self._model, "messages": messages}
        if max_tokens is not None:
            params["max_output_tokens"] = max_tokens

        if hasattr(self._client, "responses"):
            resp = self._client.responses.create(**params)
            return _extract_openai_text(resp)

        legacy_params = {"model": self._model, "messages": messages}
        if max_tokens is not None:
            legacy_params["max_tokens"] = max_tokens
        if hasattr(self._client, "ChatCompletion"):
            resp = self._client.ChatCompletion.create(**legacy_params)
            return _extract_openai_text(resp)

        raise RuntimeError("OpenAI client does not expose a supported chat API")


class LlamaCppAdapter:
    """Adapter for llama.cpp bindings."""

    def __init__(self, model_path: str | None, client: Any | None = None) -> None:
        if client is None:
            if not model_path:
                raise FileNotFoundError("model_path required for llama_cpp backend")
            try:
                from llama_cpp import Llama  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("llama_cpp backend unavailable without llama-cpp-python") from exc
            client = Llama(model_path=model_path)
        self._llama = client

    def complete(self, prompt: str, max_tokens: int | None = None) -> str:  # pragma: no cover - requires llama_cpp
        resp = self._llama(
            prompt,
            max_tokens=max_tokens if max_tokens is not None else 128,
        )
        return (resp.get("choices") or [{}])[0].get("text", "")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int | None = None) -> str:  # pragma: no cover - requires llama_cpp
        resp = self._llama.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens if max_tokens is not None else 128,
        )
        return (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")


@dataclass(slots=True)
class LLMConfig:
    backend: str = "echo"

    model_path: str | None = None
    model: str | None = None
    max_input_tokens: int | None = 4096
    max_response_tokens: int | None = 512
    forward_input_with_response: bool = False
    openai_client: Any | None = None
    llama_client: Any | None = None


class LLMClient:
    """Facade that exposes completion/chat for a configured backend."""

    def __init__(self, config: Dict[str, Any] | None = None, *, fallback_to_echo: bool = True) -> None:
        cfg = LLMConfig(**(config or {}))
        self.config = cfg
        self.backend = cfg.backend
        try:
            self._adapter = self._build_adapter(cfg)
        except Exception:
            if not fallback_to_echo:
                raise
            self._adapter = EchoAdapter()
            self.backend = "echo"

    def _build_adapter(self, cfg: LLMConfig) -> Adapter:
        if cfg.backend == "echo":
            return EchoAdapter()
        if cfg.backend == "openai":
            model = cfg.model or "gpt-4o-mini"
            return OpenAIAdapter(model, client=cfg.openai_client)
        if cfg.backend == "llama_cpp":
            if cfg.llama_client is None and not cfg.model_path:
                raise FileNotFoundError("model_path required for llama_cpp backend")
            return LlamaCppAdapter(cfg.model_path, client=cfg.llama_client)
        raise ValueError(f"Unknown backend: {cfg.backend}")

    def complete(self, prompt: str) -> str:
        return self._adapter.complete(prompt, self.config.max_response_tokens)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        return self._adapter.chat(messages, self.config.max_response_tokens)


__all__ = ["LLMClient", "LLMConfig"]

