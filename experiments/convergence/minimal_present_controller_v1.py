#!/usr/bin/env python3
"""Frozen Minimal-Present Controller v1.

Purpose: choose the next *kind* of consequential intervention from a minimal
state only. This controller is frozen before historical Test-1 cases are
selected. It must not inspect parked history, prose transcripts, or future
commits.

Input JSON keys:
  completion_satisfied: bool
  verifier_status: "DECISIVE"|"INCONCLUSIVE"|"NOT_RUN"
  scope_ok: bool
  attached: bool
  causal_status: "ESTABLISHED"|"UNTESTED"|"NOT_APPLICABLE"
  live_residual: str
  next_process_test: str

Output JSON:
  action: one of STOP, RUN_VERIFIER, REVERIFY_SAME_QUESTION, CHECK_SCOPE,
          CHECK_ATTACHMENT, ABLATE_CAUSE, EXECUTE_NEXT_PROCESS_TEST,
          LOCALIZE_RESIDUAL
  payload: exact carried field when applicable
"""

from __future__ import annotations
import json
import sys

ALLOWED_KEYS = {
    "completion_satisfied",
    "verifier_status",
    "scope_ok",
    "attached",
    "causal_status",
    "live_residual",
    "next_process_test",
}

def choose(state: dict) -> dict:
    unknown = set(state) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"non-minimal keys forbidden: {sorted(unknown)}")

    if bool(state.get("completion_satisfied", False)):
        return {"action": "STOP", "payload": ""}

    vs = state.get("verifier_status", "NOT_RUN")
    if vs == "NOT_RUN":
        return {"action": "RUN_VERIFIER", "payload": ""}
    if vs == "INCONCLUSIVE":
        return {"action": "REVERIFY_SAME_QUESTION", "payload": state.get("live_residual", "")}

    if not bool(state.get("scope_ok", False)):
        return {"action": "CHECK_SCOPE", "payload": ""}
    if not bool(state.get("attached", False)):
        return {"action": "CHECK_ATTACHMENT", "payload": state.get("live_residual", "")}

    if state.get("causal_status", "UNTESTED") == "UNTESTED":
        return {"action": "ABLATE_CAUSE", "payload": state.get("live_residual", "")}

    nxt = (state.get("next_process_test") or "").strip()
    if nxt:
        return {"action": "EXECUTE_NEXT_PROCESS_TEST", "payload": nxt}

    residual = (state.get("live_residual") or "").strip()
    if residual:
        return {"action": "LOCALIZE_RESIDUAL", "payload": residual}

    return {"action": "LOCALIZE_RESIDUAL", "payload": "NO_LIVE_RESIDUAL"}

def main() -> None:
    state = json.load(sys.stdin)
    print(json.dumps(choose(state), sort_keys=True))

if __name__ == "__main__":
    main()
