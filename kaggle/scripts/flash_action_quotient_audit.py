"""Matched real-ARC audit of the Flash-promoted ft09 action quotient.

The only behavior change is exact-state proposal compression on ten replay-
certified observations. Public worlds are development diagnostics, not sealed
holdouts. Promotion requires protected controls; useful activation is measured
rather than assumed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "flash-action-quotient-results"
PRIOR = "07fe94a80edfbb295049d4140aef14ef2b47524b"
PRIOR_AGENT_SHA = "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead"
GAMES = {
    "ft09-0d8bbf25": "aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783",
    "ls20-9607627b": "298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92",
    "vc33-5430563c": "8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd",
}
VARIANTS = ("candidate", "prior", "no_action_quotient")
audit.BASELINE = PRIOR


def agent_path(variant: str) -> Path:
    return OUT / ("prior.py" if variant == "prior" else "candidate.py")


def write(path: Path, value) -> None:
    audit.write_json(path, value)


def prepare() -> None:
    assert audit.sha(agent_path("prior").read_bytes()) == PRIOR_AGENT_SHA
    audit.AGENT = agent_path("candidate")
    for kind in ("fixture", "public"):
        path = OUT / f"{kind}.json"
        args = SimpleNamespace(
            fixtures=kind == "fixture",
            games="bt11" if kind == "fixture" else "ls20,ft09,vc33",
            environments_dir=(
                str(ROOT / "upstream-arc-agi" / "test_environment_files")
                if kind == "fixture"
                else str(OUT / "envs")
            ),
            manifest=str(path),
            max_actions=128 if kind == "fixture" else 400,
        )
        audit.prepare(args)
        manifest = json.loads(path.read_text())
        assert manifest["sdk_versions"] == {"arc-agi": "0.9.9", "arcengine": "0.9.3"}
        if kind == "public":
            assert {row["game_id"] for row in manifest["games"]} == set(GAMES)
            for row in manifest["games"]:
                filename = row["game_id"].split("-")[0] + ".py"
                assert row["files"][filename] == GAMES[row["game_id"]]
        manifest["seeds"] = [0]
        manifest["baseline_commit"] = PRIOR
        manifest["interpretation"] = "public development diagnostic, not hidden generalization"
        write(path, manifest)
    print("ARC3_FLASH_ACTION_QUOTIENT_MANIFESTS=PASS", flush=True)


def cell(args) -> None:
    manifest = json.loads((OUT / f"{args.kind}.json").read_text())
    audit.AGENT = agent_path(args.variant)
    manifest["generated_agent_sha256"] = audit.sha(audit.AGENT.read_bytes())
    path = OUT / f"{args.kind}-{args.variant}-manifest.json"
    write(path, manifest)
    old_session = audit.run_session

    def measured(policy, env, digest, **kwargs):
        policy.controller.archived_capabilities = ()
        if args.variant == "no_action_quotient":
            policy.controller.certified_action_quotient_enabled = False
        result = old_session(policy, env, digest, **kwargs)
        controller = policy.controller
        q = getattr(controller, "certified_action_quotient", None)
        result.update(
            variant=args.variant,
            prior_commit=PRIOR,
            controller=type(controller).__name__,
            flash_action_quotient_enabled=bool(
                getattr(controller, "certified_action_quotient_enabled", False)
            ),
            flash_action_quotient_states=int(getattr(q, "state_count", 0) if q else 0),
            flash_action_representatives=int(
                getattr(q, "representative_count", 0) if q else 0
            ),
            flash_action_activations=int(
                getattr(controller, "certified_action_quotient_activations", 0)
            ),
            flash_actions_removed=int(
                getattr(controller, "certified_action_quotient_actions_removed", 0)
            ),
        )
        return result

    audit.run_session = measured
    audit.cell(
        SimpleNamespace(
            manifest=str(path),
            game=args.game,
            seed=0,
            arm="full",
            output=str(OUT / f"{args.game}-{args.variant}.json"),
        )
    )


def compact(row):
    keys = (
        "max_levels", "actions", "status", "milestones", "source_counts",
        "capability_records", "distinct_observations", "terminal_failures",
        "zero_observation_change", "memory_digest",
        "flash_action_quotient_enabled", "flash_action_quotient_states",
        "flash_action_representatives", "flash_action_activations",
        "flash_actions_removed",
    )
    return {key: row[key] for key in keys}


def trajectory(row):
    return [
        (tuple(step["action"]), step["after"], step["level"], step["state"])
        for step in row["trace"]
    ]


def batch() -> None:
    records = []
    raw = {}
    for kind in ("fixture", "public"):
        manifest = json.loads((OUT / f"{kind}.json").read_text())
        for game in manifest["games"]:
            gid = game["game_id"]
            paired = {}
            for variant in VARIANTS:
                done = subprocess.run(
                    [
                        sys.executable, __file__, "cell",
                        "--kind", kind, "--game", gid, "--variant", variant,
                    ],
                    capture_output=True, text=True, timeout=55,
                )
                if done.returncode:
                    raise RuntimeError(done.stderr[-3000:] + "\n" + done.stdout[-3000:])
                row = json.loads((OUT / f"{gid}-{variant}.json").read_text())
                assert row["status"] in ("WIN", "ACTION_BOUND"), row
                assert row["actions"] == len(row["trace"]) + 1
                paired[variant] = row
                print(
                    "FLASH_ACTION_CELL="
                    + json.dumps(
                        {k: v for k, v in row.items() if k != "trace"},
                        sort_keys=True,
                    ),
                    flush=True,
                )
            assert len({row["initial_digest"] for row in paired.values()}) == 1
            raw[gid] = paired
            records.append({
                "kind": kind,
                "game_id": gid,
                "variants": {name: compact(row) for name, row in paired.items()},
            })

    fixture = next(row for row in records if row["kind"] == "fixture")["variants"]
    assert fixture["candidate"]["max_levels"] == 5
    assert fixture["candidate"]["status"] == "WIN"
    assert fixture["candidate"]["actions"] <= 73

    vc33 = next(row for row in records if row["game_id"].startswith("vc33-"))["variants"]
    assert vc33["candidate"]["milestones"][:2] == [
        {"level": 1, "actions": 64},
        {"level": 2, "actions": 93},
    ]

    ft_id = next(gid for gid in raw if gid.startswith("ft09-"))
    ft = raw[ft_id]
    assert ft["candidate"]["flash_action_activations"] > 0
    assert ft["candidate"]["flash_actions_removed"] > 0
    assert ft["prior"]["flash_action_activations"] == 0
    assert ft["no_action_quotient"]["flash_action_activations"] == 0

    candidate_trace = trajectory(ft["candidate"])
    prior_trace = trajectory(ft["prior"])
    no_q_trace = trajectory(ft["no_action_quotient"])
    changed_vs_prior = candidate_trace != prior_trace
    ablation_restores_prior = no_q_trace == prior_trace

    report = {
        "prior_commit": PRIOR,
        "interpretation": "public development diagnostic, not hidden generalization",
        "complete": True,
        "trial_count": len(records) * len(VARIANTS),
        "comparisons": records,
        "ft09_flash_effect": {
            "candidate_levels": ft["candidate"]["max_levels"],
            "prior_levels": ft["prior"]["max_levels"],
            "candidate_distinct_observations": ft["candidate"]["distinct_observations"],
            "prior_distinct_observations": ft["prior"]["distinct_observations"],
            "activations": ft["candidate"]["flash_action_activations"],
            "actions_removed": ft["candidate"]["flash_actions_removed"],
            "trajectory_changed_vs_prior": changed_vs_prior,
            "ablation_restores_prior": ablation_restores_prior,
        },
    }
    write(OUT / "comparison.json", report)
    print("FLASH_ACTION_QUOTIENT_COMPARISON=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_FLASH_ACTION_QUOTIENT_QUALIFICATION=PASS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "cell", "run"))
    parser.add_argument("--kind", choices=("fixture", "public"))
    parser.add_argument("--game")
    parser.add_argument("--variant", choices=VARIANTS)
    args = parser.parse_args()
    {"prepare": prepare, "cell": lambda: cell(args), "run": batch}[args.command]()
