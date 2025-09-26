"""Tests for the :mod:`voide.chunks` namespace package."""

from __future__ import annotations

import importlib
import pkgutil

import pytest


def test_voide_chunks_re_exports_top_level_modules() -> None:
    import chunks as top_level_chunks
    import voide.chunks as voide_chunks

    expected_modules = {
        name
        for _, name, is_pkg in pkgutil.iter_modules(top_level_chunks.__path__)
        if not is_pkg
    }

    assert expected_modules, "expected to discover top-level chunk modules"
    assert expected_modules.issubset(set(voide_chunks.__all__))

    for module_name in expected_modules:
        bridged = importlib.import_module(f"voide.chunks.{module_name}")
        try:
            direct = importlib.import_module(f"chunks.{module_name}")
        except Exception as exc:
            with pytest.raises(exc.__class__):
                dir(bridged)
            continue

        dir(bridged)  # trigger lazy load into the shared sys.modules entry
        assert (
            importlib.import_module(f"voide.chunks.{module_name}") is direct
        ), f"voide.chunks.{module_name} did not reference chunks.{module_name}"
