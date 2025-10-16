"""LLM client abstractions and lightweight fallbacks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
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


class Gpt4AllAdapter:
    """Adapter for GPT4All bindings."""

    def __init__(self, model: str | None, model_path: str | None, client: Any | None = None) -> None:
        if client is None:
            name = model or (Path(model_path).stem if model_path else None)
            if not name:
                raise ValueError("model required for gpt4all backend")
            try:
                from gpt4all import GPT4All  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("gpt4all backend unavailable without gpt4all package") from exc
            kwargs: Dict[str, Any] = {}
            if model_path:
                kwargs["model_path"] = str(Path(model_path).expanduser())
            client = GPT4All(name, **kwargs)
        self._client = client

    def complete(self, prompt: str, max_tokens: int | None = None) -> str:  # pragma: no cover - optional dependency
        if hasattr(self._client, "generate"):
            kwargs: Dict[str, Any] = {}
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            result = self._client.generate(prompt, **kwargs)
            return str(result)
        if callable(self._client):
            result = self._client(prompt, max_tokens=max_tokens)
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                text = result.get("text") or result.get("content")
                if isinstance(text, str):
                    return text
            return str(result)
        raise RuntimeError("GPT4All client does not expose a supported completion API")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int | None = None) -> str:  # pragma: no cover - optional dependency
        if hasattr(self._client, "chat_completion"):
            kwargs: Dict[str, Any] = {}
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            resp = self._client.chat_completion(messages, **kwargs)
            if isinstance(resp, dict):
                choices = resp.get("choices") or []
                if choices:
                    first = choices[0]
                    if isinstance(first, dict):
                        message = first.get("message")
                        if isinstance(message, dict):
                            content = message.get("content")
                            if isinstance(content, str):
                                return content
                        content = first.get("text")
                        if isinstance(content, str):
                            return content
                if "message" in resp and isinstance(resp["message"], str):
                    return resp["message"]
            if isinstance(resp, str):
                return resp
        last = messages[-1]["content"] if messages else ""
        return self.complete(last, max_tokens)


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
    gpt4all_client: Any | None = None
    openai_api_key: str | None = None


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
        backend = (cfg.backend or "echo").replace(".", "_")
        if backend == "echo":
            return EchoAdapter()
        if backend == "openai":
            if cfg.openai_api_key:
                os.environ["OPENAI_API_KEY"] = cfg.openai_api_key
            model = cfg.model or "gpt-4o-mini"
            return OpenAIAdapter(model, client=cfg.openai_client)
        if backend == "llama_cpp":
            if cfg.llama_client is None and not cfg.model_path:
                raise FileNotFoundError("model_path required for llama_cpp backend")
            return LlamaCppAdapter(cfg.model_path, client=cfg.llama_client)
        if backend == "gpt4all":
            if cfg.gpt4all_client is None and not (cfg.model or cfg.model_path):
                raise FileNotFoundError("model or model_path required for gpt4all backend")
            return Gpt4AllAdapter(cfg.model, cfg.model_path, client=cfg.gpt4all_client)
        raise ValueError(f"Unknown backend: {cfg.backend}")

    def complete(self, prompt: str) -> str:
        return self._adapter.complete(prompt, self.config.max_response_tokens)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        return self._adapter.chat(messages, self.config.max_response_tokens)


__all__ = ["LLMClient", "LLMConfig"]

