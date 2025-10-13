# VOIDE Project Breadcrumb

This repository hosts **VOIDE**, a modular, node-based workflow builder for LLM-centric agents.

## Project Goal
1. Allow the user to place modules from a palette onto the canvas.
2. Wire modules together by drawing lines that represent both data flow and order of operations.
3. Hit the **Build** button so the system compiles the canvas design into an executable data flow.
4. Hit the **Play** button to execute the compiled flow end-to-end.

## Key Areas
- `chunks/` – atomic operation modules (“chunks”) such as Prompt, Debate/loop, LLM, Cache, Memory, Divider, ToolCall and Log.
- `voide/` – core runtime and compiler primitives that assemble chunks into executable graphs.
- `voide_ui/` – Tk-based desktop UI for arranging nodes, configuring options, and running chat sessions.
- `tests/` – pytest suite covering assembly, graph execution, ops behavior, state persistence, and storage semantics.
- `main.py` / `main_ui.py` – console and GUI entry points.

Use the nested `Agent.md` files inside each area for deeper notes and conventions when editing specific modules, DO
NOT REMOVE ANY OTHER FUNCTIONS WHILE MODIFING FILES OR FIXING ERRORS UNLESS INSTRUCTED TO REMOVE A FUNCTION. 
