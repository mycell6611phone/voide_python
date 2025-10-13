# Core Runtime Breadcrumb

The `voide` package houses the runtime primitives that power graph assembly and execution.

## Role in the Project Goal
- **Goal 1:** Provides metadata loaders that inform the palette about available modules.
- **Goal 2:** `graph.py` validates edges and port mappings, enforcing the canvas wiring constraints.
- **Goal 3:** `assemble.py` and `compiler.py` turn the canvas design into an executable runner when Build is pressed.
- **Goal 4:** `compiler.Runner` and related helpers execute the data flow triggered by the Play button.

## Important Modules
- `assemble.py` – loads chunk metadata, validates `provides`/`requires`, and builds the shared container.
- `compiler.py` – converts serialized graphs into runnable pipelines with `Runner` objects.
- `graph.py` – defines node/edge models, JSON serialization, and Kahn topological sorting with cycle detection.
- `errors.py` – shared exception types for assembly/graph issues.
- `storage.py` – persistence utilities backing cache and memory implementations.
- `llm_client.py` – unifies chat vs completion backends and the echo fallback client.
- `chunk_api.py` – data classes and helpers that chunks use when registering ops/tools.

### Conventions
- Keep public APIs stable: tests import `assemble`, `Graph`, and `Runner` directly.
- When adding new chunk types, ensure `assemble.py` discovers them and exposes any new container keys.
- `chunk_api.scan_chunk_files` now always runs recursive globs (`**`) correctly and filters to real files before sorting.
- `compiler.Runner` maps edge ports by checking node `outputs` metadata and falls back to single-output inference; single inbound edges also expose the full upstream payload for convenience.
- `llm_client.LLMClient` supports injecting stub `openai_client`/`llama_client` instances, so prefer dependency injection during tests or when wiring alternative adapters.
