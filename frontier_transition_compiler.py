"""Compile a verifier artifact into a stale-safe candidate frontier transition.

This tool never edits program_frontier.json. It verifies that the artifact
consumed the currently authoritative state and emits a candidate transition for
review/CI. Truth remains in the external verifier; this only compiles state.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path


def canonical(x: object) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--out", default="artifacts/candidate_frontier_transition.json")
    args = ap.parse_args()
    frontier = json.load(open("program_frontier.json"))
    artifact = json.load(open(args.artifact))
    assert frontier.get("authoritative") is True
    consumed = artifact.get("consumed_frontier")
    assert isinstance(consumed, dict), "artifact has no consumed_frontier"
    assert consumed.get("schema_version") == frontier.get("schema_version"), "STALE_SCHEMA"
    assert consumed.get("live_state_parent_sha") == frontier.get("live_state_parent_sha"), "STALE_FRONTIER_PARENT"
    assert consumed.get("live_residual") == frontier.get("live_residual"), "STALE_LIVE_RESIDUAL"
    proposed = artifact.get("proposed_transition")
    assert isinstance(proposed, dict) and proposed.get("classification"), "NO_EXPLICIT_TRANSITION"
    candidate = {
        "source_frontier_schema": frontier["schema_version"],
        "source_frontier_parent": frontier["live_state_parent_sha"],
        "source_frontier_fingerprint": hashlib.sha256(canonical(frontier)).hexdigest(),
        "artifact": args.artifact,
        "artifact_fingerprint": hashlib.sha256(canonical(artifact)).hexdigest(),
        "classification": proposed["classification"],
        "scope": proposed.get("scope"),
        "candidate_live_residual": proposed.get("residual"),
        "mutation_applied": False,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
    print(json.dumps(candidate, indent=2, sort_keys=True))
    print("CANDIDATE_FRONTIER_TRANSITION_COMPILED")


if __name__ == "__main__":
    main()
