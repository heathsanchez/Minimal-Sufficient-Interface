"""Targeted MG-ARC5 probe mismatch diagnostic on frozen development worlds."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "requalification-results"


def run_one(kind: str, game_id: str, max_actions: int) -> dict:
    from arc_agi import Arcade, OperationMode

    import requalification_audit as rq

    manifest = json.loads((OUT / f"{kind}.json").read_text())
    audit.AGENT = OUT / "candidate.py"
    manifest["generated_agent_sha256"] = audit.sha(audit.AGENT.read_bytes())

    row = next(item for item in manifest["games"] if item["game_id"] == game_id)
    if audit.file_hashes(Path(row["local_dir"])) != row["files"]:
        raise ValueError("frozen environment source mismatch")

    module = audit.load_agent()
    audit.block_network()
    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=manifest["environments_dir"],
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("pinned offline environment unavailable")

    policy = module.MyAgent(
        card_id="local-audit",
        game_id="probe-diagnostic",
        agent_name="frozen",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()
    controller = policy.controller
    witnesses = []
    original = controller._record_effect

    def traced(frame, obs):
        pending = getattr(controller, "_pending_effect", None)
        source = getattr(getattr(controller, "_last_action", None), "source", None)
        expected = getattr(controller, "_pending_probe_expected", None)
        if pending is not None and source == "transfer_probe" and expected is not None:
            _context, action, before, descriptor, _history = pending
            grid = module.settled_grid(frame)
            observed = (
                len(getattr(controller, "_episode_certificate", ())),
                tuple(action),
                str(descriptor),
                controller._structural_signature(before, grid, action),
            )
            witnesses.append(
                {
                    "target_level": int(obs.levels_completed),
                    "expected": expected,
                    "observed": observed,
                    "same_action": tuple(observed[1]) == tuple(expected[1]),
                    "same_descriptor": observed[2] == expected[2],
                    "same_structural": tuple(observed[3]) == tuple(expected[3]),
                }
            )
        return original(frame, obs)

    controller._record_effect = traced
    result = audit.run_session(
        policy,
        env,
        lambda observation: module.normalize_frame(observation).evidence_sha256,
        max_actions=max_actions,
        wall_seconds=30,
    )
    arc.close_scorecard()
    return {
        "kind": kind,
        "game_id": game_id,
        "max_levels": result["max_levels"],
        "milestones": result["milestones"],
        "probe_witnesses": witnesses,
    }


def main() -> None:
    fixture = json.loads((OUT / "fixture.json").read_text())
    public = json.loads((OUT / "public.json").read_text())
    bt11 = fixture["games"][0]["game_id"]
    vc33 = next(row["game_id"] for row in public["games"] if row["game_id"].startswith("vc33-"))
    report = {
        "bt11": run_one("fixture", bt11, 20),
        "vc33": run_one("public", vc33, 110),
    }
    path = OUT / "probe-diagnostic.json"
    audit.write_json(path, report)
    print("MG_ARC5_PROBE_DIAGNOSTIC=" + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
