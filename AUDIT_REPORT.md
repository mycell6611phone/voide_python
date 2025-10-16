# VOIDE Code Audit

## Scope & Methodology
- Reviewed runtime core (`voide/`), chunk modules (`chunks/`), UI toolkit (`voide_ui/`), and legacy helpers.
- Ran `pytest` to confirm the bundled unit tests currently pass (36 tests).
- Traced UI node definitions through to registered chunk implementations to verify Build/Play compatibility.

## Findings

### Palette Type Map Diverges from Available Chunks
- The UI palette advertises `"Debate/Loop"` and `"Tool Call"` nodes that map to type names (`DebateLoop`, `ToolCall`) lacking corresponding chunk modules, so building a graph that includes either node will fail with `Unknown op` at runtime.
- The same palette maps `"Divider"` to the type name `Divider`, but the only divider chunk registers the op under `"DividerGate"`, meaning divider nodes also fail during execution.

### Divider Wiring Metadata Out of Sync With Chunk Contract
- `GraphCanvas.PORTS` declares divider outputs as `["A", "B"]`, yet the actual chunk emits keys `"pass"`, `"divert"`, and `"trigger"`. Any edges drawn from divider nodes will therefore use nonexistent port names, breaking runner payload routing.
- `DividerOptionsWindow` prompts users to supply a custom value→port mapping (`mapping`), but the divider chunk ignores that configuration entirely and only supports truthy rule/trigger routing, so the options dialog misleads users and stores dead configuration.

### Legacy `ui.py` Artifact Is Corrupted
- The legacy `ui.py` module duplicates the state/canvas helpers but is truncated mid-string and also lacks imports for `dataclass`, `json`, and typing, leaving the file unusable if imported.

### Graph Deserialization Drops Port Metadata
- `Graph.from_dict` rebuilds each node with only `id`, `type_name`, and `config`, silently discarding serialized `inputs`/`outputs` data. Downstream tools relying on saved port metadata will lose information when reloading graphs.

## Suggested Remediation
1. Update the palette (`LABEL_TO_TYPE`) and port metadata (`GraphCanvas.PORTS`) to align with the actual chunks, or implement the advertised `DebateLoop`/`ToolCall` chunks.
2. Either adjust the divider chunk/UI to share a single contract or rewrite the options panel and port list to match the current `DividerGate` behavior.
3. Remove or repair the corrupted `ui.py` artifact to avoid accidental imports.
4. Extend `Graph.from_dict` to restore `inputs` and `outputs` so saved graphs maintain port metadata fidelity.

## Test Run
- `pytest` (36 tests, all passing).
 
