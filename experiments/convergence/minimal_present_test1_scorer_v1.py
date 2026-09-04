#!/usr/bin/env python3
"""Frozen conservative scorer/reconstructor for Minimal-Present Test 1.

Scientific rule: historical cases are UNSCORABLE unless the pre-existing
frontier contains explicit machine-readable evidence for every controller
field needed to determine the action and for the historical next-action class.
No semantic inference from result IDs, commit messages, branch names, or prose.
"""
from __future__ import annotations
import json

DECISIVE = {"SAT", "UNSAT", "PASS", "FAIL", "VERIFIED", "DECISIVE", "SUCCESS"}
INCONCLUSIVE = {"UNKNOWN", "TIMEOUT", "INCONCLUSIVE"}
NOT_RUN = {"NOT_RUN", "PENDING", "UNEXECUTED"}
ACTION_CLASSES = {
    "STOP", "RUN_VERIFIER", "REVERIFY_SAME_QUESTION", "CHECK_SCOPE",
    "CHECK_ATTACHMENT", "ABLATE_CAUSE", "EXECUTE_NEXT_PROCESS_TEST",
    "LOCALIZE_RESIDUAL"
}

# Exact explicit key aliases allowed. No text parsing is permitted.
ALIASES = {
    "completion_satisfied": ["completion_satisfied"],
    "verifier_status": ["verifier_status", "verification_status"],
    "scope_ok": ["scope_ok", "claim_scope_verified"],
    "attached": ["attached", "attachment_verified"],
    "causal_status": ["causal_status", "ablation_status"],
    "next_action_class": ["next_action_class", "action_class"],
}

def first_explicit(frontier: dict, aliases: list[str]):
    for key in aliases:
        if key in frontier:
            return frontier[key]
        if isinstance(frontier.get("controller_state"), dict) and key in frontier["controller_state"]:
            return frontier["controller_state"][key]
        if isinstance(frontier.get("last_transition"), dict) and key in frontier["last_transition"]:
            return frontier["last_transition"][key]
    return None

def normalize_verifier(v):
    if v is None: return None
    s = str(v).upper()
    if s in DECISIVE: return "DECISIVE"
    if s in INCONCLUSIVE: return "INCONCLUSIVE"
    if s in NOT_RUN: return "NOT_RUN"
    return None

def reconstruct_minimal(frontier: dict):
    missing = []
    state = {}
    v = first_explicit(frontier, ALIASES["completion_satisfied"])
    if not isinstance(v, bool): missing.append("completion_satisfied")
    else: state["completion_satisfied"] = v

    v = normalize_verifier(first_explicit(frontier, ALIASES["verifier_status"]))
    if v is None: missing.append("verifier_status")
    else: state["verifier_status"] = v

    for key in ("scope_ok", "attached"):
        v = first_explicit(frontier, ALIASES[key])
        if not isinstance(v, bool): missing.append(key)
        else: state[key] = v

    v = first_explicit(frontier, ALIASES["causal_status"])
    if v not in {"ESTABLISHED", "UNTESTED", "NOT_APPLICABLE"}:
        missing.append("causal_status")
    else: state["causal_status"] = v

    lr = frontier.get("live_residual")
    if isinstance(lr, dict) and isinstance(lr.get("text"), str):
        state["live_residual"] = lr["text"]
    else:
        missing.append("live_residual")

    npt = frontier.get("next_process_test")
    if isinstance(npt, str): state["next_process_test"] = npt
    else: missing.append("next_process_test")
    return state, missing

def historical_action(frontier: dict):
    v = first_explicit(frontier, ALIASES["next_action_class"])
    return v if v in ACTION_CLASSES else None

def scoreability(frontier: dict):
    state, missing = reconstruct_minimal(frontier)
    actual = historical_action(frontier)
    if actual is None: missing.append("historical_next_action_class")
    return {"scorable": not missing, "minimal_state": state,
            "historical_action_class": actual, "missing": missing}

if __name__ == "__main__":
    import sys
    f = json.load(sys.stdin)
    print(json.dumps(scoreability(f), indent=2, sort_keys=True))
