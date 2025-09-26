from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable, List


def load_scan_chunk_files() -> Callable[[str], List[Path]]:
    module_path = Path(__file__).resolve().parents[1] / "voide" / "chunk_api.py"
    spec = importlib.util.spec_from_file_location("voide.chunk_api_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.scan_chunk_files


scan_chunk_files = load_scan_chunk_files()


def create_chunk(dir_path: Path, name: str) -> Path:
    path = dir_path / f"{name}.py"
    path.write_text("# chunk\n", encoding="utf-8")
    return path


def test_scan_chunk_files_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chunks_dir = Path("chunks")
    chunks_dir.mkdir()

    file_a = create_chunk(chunks_dir, "a")
    file_b = create_chunk(chunks_dir, "b")

    results = scan_chunk_files("chunks/*.py")

    assert results == [Path("chunks/a.py"), Path("chunks/b.py")]
    # Ensure paths resolve to the created files.
    assert [p.resolve() for p in results] == [file_a.resolve(), file_b.resolve()]


def test_scan_chunk_files_absolute(tmp_path):
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()

    file_a = create_chunk(chunks_dir, "a")
    file_b = create_chunk(chunks_dir, "b")

    results = scan_chunk_files(str(chunks_dir / "*.py"))

    assert results == sorted([file_a, file_b])


def test_scan_chunk_files_absolute_recursive(tmp_path):
    chunks_dir = tmp_path / "chunks"
    nested_dir = chunks_dir / "nested"
    nested_dir.mkdir(parents=True)

    top_file = create_chunk(chunks_dir, "top")
    nested_file = create_chunk(nested_dir, "inner")

    results = scan_chunk_files(str(chunks_dir / "**" / "*.py"))

    assert results == sorted([top_file, nested_file])
