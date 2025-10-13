# Chunks Module Breadcrumb

This directory contains the plug-in “chunk” modules that VOIDE assembles into workflows.

## Role in the Project Goal
- **Palette population (Goal 1):** Each file here defines a module that appears in the UI palette, including its inputs/outputs and configuration schema.
- **Data flow semantics (Goal 2):** Chunk metadata declares required/produced ports so wiring on the canvas maps cleanly to runtime edges.
- **Build pipeline (Goal 3):** When the Build button is pressed, `assemble` imports these chunks to register ops in the container.
- **Execution (Goal 4):** At Play time, the concrete ops defined here process payloads in the compiled runner.

## Contents
- `prompt.py` – renders User  prompts (`{task}` default) before sending to downstream ops.
- `llm.py` – wraps the LLM client, supporting chat/completion backends.
- `cache.py` – caches model responses with TTL-aware `prefer`/`refresh` strategies; delegates to child ops when misses occur.
- `memory.py` – shares the `MemoryStore` container resource for persisting and querying keyed payloads.
- `divider.py` – routing gate with AND/OR rules to send packets to `pass`, `divert`, or `trigger` ports.
- `log.py` – expected JSONL logger chunk for observability (see tests for intended behavior).

### Notes
- Each chunk exposes a `build(container)` hook and registers operations via the shared container.
- Tests in `tests/test_memory_cache_log.py` and `tests/test_ops_prompt_llm.py` encode contract expectations.
