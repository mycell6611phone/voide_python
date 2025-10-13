# UI Layer Breadcrumb

This package implements the Tkinter desktop application used to design and run VOIDE workflows.

## Role in the Project Goal
- **Goal 1:** `app.py` renders the module palette and spawns canvas nodes for selected chunks.
- **Goal 2:** `canvas.py` manages drag-to-wire interactions and keeps graph edges in sync with the visual links.
- **Goal 3:** The Build command invokes `voide.assemble`/`voide.compiler` with the current canvas layout.
- **Goal 4:** The Play command streams runner output to the chat/console panes for live execution feedback.

## Components
- `app.py` – orchestrates the palette, canvas, menus, persistence, and run controls.
- `canvas.py` – provides the draggable node editor, wiring logic, and Graph ↔ canvas conversions.
- `state.py` – saves/loads canvas layouts, node metadata, and positional information.
- `options.py` – node-specific configuration dialogs (LLM backend, prompt templates, cache TTL, etc.).
- `chat.py` – chat window UI for interactive pipeline execution.

### Usage Notes
- Canvas nodes correspond to chunk modules exposed via `assemble()`.
- The UI invokes `voide.assemble` and `voide.compiler` to compile and run flows.
