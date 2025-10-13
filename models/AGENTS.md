# /models — Offline Model Manifest
> **File Modification Guardrails**

This directory describes the default LLM/tooling bundle that ships with VOIDE.

## Role in the Project Goal
- **Goal 1:** Provides palette metadata so model-powered modules can be listed with accurate labels/capabilities.
- **Goal 3 & 4:** Guarantees the runtime can resolve local model identifiers when building and executing flows without network access.

## Files
- `models.json` — Describes available LLMs/tooling for offline installs.

## Guidelines
- Ensure license metadata satisfies the allowlist (MIT, Apache-2.0, BSD, ISC).
- Keep IDs stable; flows saved from the canvas reference these strings during Build/Play cycles.

