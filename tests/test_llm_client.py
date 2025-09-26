

from voide.llm_client import LLMClient

def test_echo_backend_complete():
    c = LLMClient({"backend": "echo"})
    assert c.complete("hello") == "ECHO: hello"

def test_fallback_when_backend_missing():
    c = LLMClient({"backend": "openai"})
    out = c.complete("hi")
    assert out.startswith("ECHO:")

    c2 = LLMClient({"backend": "llama_cpp", "model_path": "nonexistent.gguf"})
    out2 = c2.complete("hi2")
    assert out2.startswith("ECHO:")

