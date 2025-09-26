# Test Suite Breadcrumb

Pytest-based regression suite covering the runtime, chunks, and UI persistence APIs.

## Key Files
- `test_assemble.py` – validates chunk discovery, dependency handling, and container population.
- `test_graph_compile.py` – exercises graph serialization, topological ordering, and runner execution.
- `test_ops_prompt_llm.py` – asserts prompt formatting, LLM invocation semantics, and fallback behavior.
- `test_memory_cache_log.py` – covers cache TTL logic, memory store persistence, and logging expectations.
- `test_state_io.py` – ensures UI state save/load round-trips with node positions and configuration data.

### Running Tests
Use `pytest` from the repository root after setting up any required environment variables for LLM backends (tests default to the echo client).
