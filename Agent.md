# VOIDE Project Breadcrumb

This repository hosts **VOIDE**, a modular, node-based workflow builder for LLM-centric agents.

## Key Areas
- `chunks/` – atomic operation modules (“chunks”) such as Prompt, LLM, Cache, Memory, Divider, and Log.
- `voide/` – core runtime and compiler primitives that assemble chunks into executable graphs.
- `voide_ui/` – Tk-based desktop UI for arranging nodes, configuring options, and running chat sessions.
- `tests/` – pytest suite covering assembly, graph execution, ops behavior, state persistence, and storage semantics.
- `main.py` / `main_ui.py` – console and GUI entry points.

Use the nested `Agent.md` files inside each area for deeper notes and conventions when editing specific modules.
