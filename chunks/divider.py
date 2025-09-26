"""
DividerGate chunk: configurable AND/OR routing gate as a VOIDE operation.

Config keys:
  mode: "AND" | "OR" (default: "AND")
  max_steps: int (default: 100)
  rules: list[str]  # packet fields that must be truthy
  triggers: list[str]  # named triggers
  trigger_states: dict mapping trigger name to bool

Outputs:
  returns a dict with any of the keys 'pass', 'divert', 'trigger' containing the packet routed.
"""
from __future__ import annotations
from typing import Any, Dict, List

# Copy of the minimal Divider implementation
RouteHandler = Any  # in this context, handlers just capture packets

class Divider:
    __slots__ = ("mode", "rules", "triggers", "outputs", "max_steps", "_steps")

    def __init__(self, mode: str = "AND", max_steps: int = 100):
        m = mode.upper()
        if m not in ("AND", "OR"):
            raise ValueError("mode must be 'AND' or 'OR'")
        self.mode: str = m
        self.rules: List = []
        self.triggers: Dict[str, bool] = {}
        self.outputs: Dict[str, RouteHandler] = {}
        self.max_steps: int = max(1, max_steps)
        self._steps: int = 0

    def add_rule(self, field: str) -> None:
        # rule checks truthiness of a packet field
        self.rules.append(lambda p, f=field: bool(p.get(f)))

    def add_trigger(self, name: str) -> None:
        self.triggers[name] = False

    def set_trigger(self, name: str, state: bool = True) -> None:
        if name not in self.triggers:
            raise KeyError(f"unknown trigger: {name}")
        self.triggers[name] = state

    def connect_output(self, name: str, handler: RouteHandler) -> None:
        if name not in ("pass", "divert", "trigger"):
            raise ValueError("output name must be 'pass', 'divert', or 'trigger'")
        self.outputs[name] = handler

    def _rules_pass(self, data: Dict[str, Any]) -> bool:
        if not self.rules:
            return True
        results = (r(data) for r in self.rules)
        return all(results) if self.mode == "AND" else any(results)

    def _has_trigger(self) -> bool:
        return any(self.triggers.values())

    def route(self, data: Dict[str, Any]) -> None:
        if self._steps >= self.max_steps:
            if "divert" in self.outputs:
                self.outputs["divert"]({**data, "_error": "max_steps_exceeded"})
            return
        self._steps += 1

        if self._has_trigger() and "trigger" in self.outputs:
            self.outputs["trigger"](data)
            return

        handler = self.outputs.get("pass") if self._rules_pass(data) else self.outputs.get("divert")
        if handler:
            handler(data)

# VOIDE op wrapper
provides = ["ops"]
requires: List[str] = []

def op_divider_gate(message: Dict[str, Any], config: Dict[str, Any], container: Dict[str, Any]) -> Dict[str, Any]:
    # instantiate or reuse a Divider per op invocation
    gate = Divider(mode=config.get("mode", "AND"), max_steps=int(config.get("max_steps", 100)))
    # configure rules
    for field in config.get("rules", []):
        gate.add_rule(field)
    # configure triggers
    for trig in config.get("triggers", []):
        gate.add_trigger(trig)
        if config.get("trigger_states", {}).get(trig, False):
            gate.set_trigger(trig, True)
    # prepare result capture
    result: Dict[str, Any] = {}
    gate.connect_output("pass", lambda pkt: result.update({"pass": pkt}))
    gate.connect_output("divert", lambda pkt: result.update({"divert": pkt}))
    gate.connect_output("trigger", lambda pkt: result.update({"trigger": pkt}))
    # route the message
    gate.route(message)
    return result


def build(container: Dict[str, Any]) -> None:
    container.setdefault("ops", {})["DividerGate"] = op_divider_gate

