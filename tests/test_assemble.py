

from pathlib import Path
import textwrap

from voide.assemble import assemble, UnresolvedDependenciesError

def write_chunk(dir: Path, name: str, body: str) -> Path:
    p = dir / f"{name}.py"
    p.write_text(textwrap.dedent(body))
    return p

def test_assemble_simple(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()

    # Provider chunk A
    write_chunk(
        chunks,
        "a",
        """
provides = ["A"]
requires = []
def build(container):
    container["A"] = 1
"""
    )

    # Consumer chunk B
    write_chunk(
        chunks,
        "b",
        """
provides = ["B"]
requires = ["A"]
def build(container):
    container["B"] = container["A"] + 1
"""
    )

    c = assemble(chunks_glob=str(chunks / "*.py"))
    assert c["A"] == 1
    assert c["B"] == 2

def test_unresolved_dependencies(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()

    # A chunk that requires a missing key
    write_chunk(
        chunks,
        "needs_x",
        """
provides = ["Y"]
requires = ["X"]
def build(container):
    container["Y"] = 42
"""
    )

    try:
        assemble(chunks_glob=str(chunks / "*.py"))
        assert False, "expected UnresolvedDependenciesError"
    except UnresolvedDependenciesError as e:
        msg = str(e)
        assert "X" in msg


def test_assemble_default_loads_builtin_chunks():
    container = assemble()
    ops = container.get("ops", {})

    assert "Prompt" in ops
    assert "LLM" in ops
    assert "llm_client" in container


def test_hidden_chunks_are_skipped(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()

    write_chunk(
        chunks,
        "public",
        """
provides = ["ops"]
requires = []

def build(container):
    container.setdefault("ops", {})["Public"] = lambda *args, **kwargs: {"result": "ok"}
""",
    )

    write_chunk(
        chunks,
        "_private",
        """
provides = ["ops"]
requires = []

def build(container):
    container.setdefault("ops", {})["Hidden"] = lambda *args, **kwargs: {"result": "hidden"}
""",
    )

    container = assemble(chunks_glob=str(chunks / "*.py"))
    ops = container.get("ops", {})

    assert "Public" in ops
    assert "Hidden" not in ops

