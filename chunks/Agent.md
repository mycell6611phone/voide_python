# Chunks Module Breadcrumb

This directory contains the plug-in “chunk” modules that VOIDE assembles into workflows.

## Contents
- `prompt.py` – renders templated prompts (`{task}` default) before sending to downstream ops.
- `llm.py` – wraps the LLM client, supporting chat/completion backends and graceful fallback to an echo responder.
- `cache.py` – caches model responses with TTL-aware `prefer`/`refresh` strategies; delegates to child ops when misses occur.
- `memory.py` – shares the `MemoryStore` container resource for persisting and querying keyed payloads.
- `divider.py` – routing gate with AND/OR rules to send packets to `pass`, `divert`, or `trigger` ports.
- `log.py` – expected JSONL logger chunk for observability (see tests for intended behavior).

### Notes
- Each chunk exposes a `build(container)` hook and registers operations via the shared container.
- Tests in `tests/test_memory_cache_log.py` and `tests/test_ops_prompt_llm.py` encode contract expectations.
