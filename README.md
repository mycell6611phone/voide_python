Project Overview
VOIDE is a visual data-flow editor that lets you assemble and run AI pipelines without writing orchestration code. Here’s how it works:

Palette & Canvas

Modules (nodes) live in a scrollable palette on the left. Available modules include:

LLM (large language model)

Prompt (prepare model inputs)

Debate/Loop (iterative reasoning)

Memory (persist and query context)

Log (JSONL activity logging)

Divider (conditional routing)

Tool Call (invoke external tools)

UI (entry-point for chat)

Drag or double-click any module to drop it onto the canvas.

Wiring Tool

Click and drag from a module’s output port (green dot) to an input port (blue dot) on another module to draw a connection.

These wires define the order of operations and the data fields that flow between modules.

Node Configuration

Left-click a node to open its options dialog (e.g. choose an LLM backend, set prompt templates, configure cache TTL, etc.).

Right-click a node to open a context menu with commands: Copy, Cut, Paste, Reverse Inputs, and Delete.

Top Menu & Toolbar

File menu (New, Open, Save, Close, project settings like CPU/GPU)

System menu for global preferences

Play / Pause / Stop buttons in the center run, pause, or terminate the data flow

Build button at upper-right compiles your canvas design into an executable pipeline by topo-sorting and wiring together the underlying Python “chunk” modules.

Interactive Chat

Place the UI module on the canvas, wire it into your flow, then click Chat or the ▶ Play button to launch a GPT-style window.

Type input messages and see the flow’s output in real time, just as if you’d coded the pipeline by hand.

With VOIDE you get true drag-and-drop assembly of modular AI building-blocks, visual wiring, and instant execution—all without leaving the GUI.
