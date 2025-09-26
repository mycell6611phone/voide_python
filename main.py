from __future__ import annotations

from voide import assemble

def main() -> None:
    container = assemble()
    ready = sorted(k for k in container.keys() if k not in {"config", "ops", "tools"})
    print("READY:", ", ".join(ready) if ready else "<none>")


if __name__ == "__main__":
    main()
