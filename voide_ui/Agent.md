# UI Layer Breadcrumb

This package implements the Tkinter desktop application used to design and run VOIDE workflows.

## Components
- `app.py` – orchestrates the palette, canvas, menus, persistence, and run controls.
- `canvas.py` – provides the draggable node editor, wiring logic, and Graph ↔ canvas conversions.
- `state.py` – saves/loads canvas layouts, node metadata, and positional information.
- `options.py` – node-specific configuration dialogs (LLM backend, prompt templates, cache TTL, etc.).
- `chat.py` – chat window UI for interactive pipeline execution.

### Usage Notes
- Canvas nodes correspond to chunk modules exposed via `assemble()`.
- The UI invokes `voide.assemble` and `voide.compiler` to compile and run flows.
