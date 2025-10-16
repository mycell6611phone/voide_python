from __future__ import annotations

from typing import Any, Dict, List

import pytest

from voide import llm_client as module


class _QueueingResponses:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._queue: List[Any] = []

    def push(self, payload: Any) -> None:
        self._queue.append(payload)

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self._queue:
            raise AssertionError("No payload queued for OpenAI response")
        return self._queue.pop(0)


class _StubOpenAIClient:
    def __init__(self, responses: _QueueingResponses) -> None:
        self.responses = responses


class _StubLlamaClient:
    def __init__(self) -> None:
        self.completions: List[Dict[str, Any]] = []
        self.chat_completions: List[Dict[str, Any]] = []

    def __call__(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        self.completions.append({"prompt": prompt, **kwargs})
        return {"choices": [{"text": "llama completion"}]}

    def create_chat_completion(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        self.chat_completions.append({"messages": messages, **kwargs})
        return {"choices": [{"message": {"content": "llama chat"}}]}


class _StubGpt4AllClient:
    def __init__(self) -> None:
        self.generations: List[Dict[str, Any]] = []
        self.chats: List[Dict[str, Any]] = []

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.generations.append({"prompt": prompt, **kwargs})
        return "gpt4all completion"

    def chat_completion(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        self.chats.append({"messages": messages, **kwargs})
        return {"choices": [{"message": {"content": "gpt4all chat"}}]}


def test_echo_backend_complete_and_chat() -> None:
    client = module.LLMClient({"backend": "echo"})
    assert client.complete("hello") == "ECHO: hello"
    assert (
        client.chat([
            {"role": "user", "content": "greetings"},
            {"role": "assistant", "content": "ack"},
            {"role": "user", "content": "ping"},
        ])
        == "ECHO: ping"
    )


def test_openai_adapter_delegation() -> None:
    responses = _QueueingResponses()
    responses.push(type("Resp", (), {"output_text": "openai completion"})())
    responses.push({"choices": [{"message": {"content": "openai chat"}}]})
    stub_client = _StubOpenAIClient(responses)

    client = module.LLMClient(
        {
            "backend": "openai",
            "model": "gpt-test",
            "openai_client": stub_client,
            "max_response_tokens": 77,
        }
    )

    assert client.backend == "openai"
    assert client.complete("tell me a joke") == "openai completion"
    assert responses.calls[0]["model"] == "gpt-test"
    assert responses.calls[0]["input"] == "tell me a joke"
    assert responses.calls[0]["max_output_tokens"] == 77

    messages = [{"role": "user", "content": "chat?"}]
    assert client.chat(messages) == "openai chat"
    assert responses.calls[1]["messages"] == messages
    assert responses.calls[1]["max_output_tokens"] == 77


def test_llama_cpp_adapter_delegation() -> None:
    stub_client = _StubLlamaClient()
    client = module.LLMClient(
        {
            "backend": "llama_cpp",
            "model_path": "fake-model.gguf",
            "llama_client": stub_client,
            "max_response_tokens": 21,
        }
    )

    assert client.backend == "llama_cpp"
    assert client.complete("Write a haiku") == "llama completion"
    assert stub_client.completions == [{"prompt": "Write a haiku", "max_tokens": 21}]

    messages = [{"role": "user", "content": "Respond in kind"}]
    assert client.chat(messages) == "llama chat"
    assert stub_client.chat_completions == [{"messages": messages, "max_tokens": 21}]


def test_llama_backend_accepts_dot_variant() -> None:
    stub_client = _StubLlamaClient()
    client = module.LLMClient(
        {
            "backend": "llama.cpp",
            "model_path": "fake-model.gguf",
            "llama_client": stub_client,
            "max_response_tokens": 13,
        }
    )

    assert client.backend == "llama.cpp"
    assert client.complete("demo") == "llama completion"
    assert stub_client.completions[-1]["max_tokens"] == 13


def test_fallback_to_echo_when_adapter_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def raising_adapter(*_: Any, **__: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "OpenAIAdapter", raising_adapter)

    client = module.LLMClient({"backend": "openai"})
    assert client.backend == "echo"
    assert client.complete("fallback please").startswith("ECHO:")


def test_disable_fallback_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def raising_adapter(*_: Any, **__: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "LlamaCppAdapter", raising_adapter)

    with pytest.raises(RuntimeError):
        module.LLMClient({"backend": "llama_cpp", "model_path": "fake.gguf"}, fallback_to_echo=False)


def test_missing_llama_model_path_triggers_echo_fallback() -> None:
    client = module.LLMClient({"backend": "llama_cpp"})
    assert client.backend == "echo"
    assert client.complete("just echo").startswith("ECHO:")


def test_gpt4all_adapter_delegation() -> None:
    stub_client = _StubGpt4AllClient()
    client = module.LLMClient(
        {
            "backend": "gpt4all",
            "model": "custom-model",
            "model_path": "/models/custom-model.gguf",
            "gpt4all_client": stub_client,
            "max_response_tokens": 55,
        }
    )

    assert client.backend == "gpt4all"
    assert client.complete("Say hi") == "gpt4all completion"
    assert stub_client.generations == [{"prompt": "Say hi", "max_tokens": 55}]

    messages = [{"role": "user", "content": "chat please"}]
    assert client.chat(messages) == "gpt4all chat"
    assert stub_client.chats == [{"messages": messages, "max_tokens": 55}]


def test_missing_gpt4all_model_info_triggers_echo_fallback() -> None:
    client = module.LLMClient({"backend": "gpt4all"})
    assert client.backend == "echo"
    assert client.complete("fallback").startswith("ECHO:")
