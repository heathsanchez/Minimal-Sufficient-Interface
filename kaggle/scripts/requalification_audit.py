"""Matched public DEVELOPMENT diagnostic for MG-ARC5 certified requalification.

This reuses the source-blind evaluator. Public worlds are development diagnostics,
not sealed holdouts. A finite prefix match is recorded only as bounded
requalification evidence, never whole-world behavioral equivalence.
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
OUT = ROOT / "kaggle" / "requalification-results"
PRIOR = "42dec1f23e243f9f3e288f57fc73833cde6c3c69"
PRIOR_AGENT_SHA = "1d9a3d9c130ee049e6428b6c87b80186756dead840086a6b68d7357960009000"
GAMES = {
    "ft09-0d8bbf25": "aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783",
    "ls20-9607627b": "298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92",
    "vc33-5430563c": "8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd",
}
VARIANTS = ("candidate", "prior", "no_transfer", "no_affordance")
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
        assert {"kind", "games", "sdk_versions", "max_actions", "generated_agent_sha256"} <= set(manifest)
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
    print("ARC3_REQUALIFICATION_MANIFESTS=PASS", flush=True)


def cell(args) -> None:
    manifest = json.loads((OUT / f"{args.kind}.json").read_text())
    audit.AGENT = agent_path(args.variant)
    manifest["generated_agent_sha256"] = audit.sha(audit.AGENT.read_bytes())
    path = OUT / f"{args.kind}-{args.variant}-manifest.json"
    write(path, manifest)

    original = audit.apply_ablation

    def configure(policy, arm):
        original(policy, arm)
        if args.variant == "no_affordance":
            policy.controller.affordances.affordance_score = lambda descriptor: 0.0

    audit.apply_ablation = configure
    old_session = audit.run_session

    def measured(policy, env, digest, **kwargs):
        result = old_session(policy, env, digest, **kwargs)
        snapshot = json.loads(policy.controller.memory.text().splitlines()[1])
        trials = snapshot.get("transfer_trials", [])
        totals: dict[str, int] = {}
        statuses: dict[str, int] = {}
        matched: dict[str, int] = {}
        for trial in trials:
            level = str(trial["target_level"])
            totals[level] = totals.get(level, 0) + int(trial["issued"])
            status = str(trial["status"])
            statuses[status] = statuses.get(status, 0) + 1
            matched[level] = max(matched.get(level, 0), int(trial.get("matched", 0)))
        result["transfer_issued_by_target"] = totals
        result["transfer_trial_statuses"] = statuses
        result["matched_checkpoints_by_target"] = matched
        result["capability_contract_records"] = len(snapshot.get("capability_contracts", []))
        result["memory_format"] = policy.controller.memory.VERSION
        result["variant"] = args.variant
        result["controller"] = type(policy.controller).__name__
        result["prior_commit"] = PRIOR
        if args.variant != "prior":
            assert all(value <= policy.controller.max_transfer_depth for value in totals.values())
            speculative = (
                result["source_counts"].get("transfer", 0)
                + result["source_counts"].get("transfer_probe", 0)
            )
            assert speculative <= sum(totals.values())
        return result

    audit.run_session = measured
    audit.cell(
        SimpleNamespace(
            manifest=str(path),
            game=args.game,
            seed=0,
            arm="no_transfer" if args.variant == "no_transfer" else "full",
            output=str(OUT / f"{args.game}-{args.variant}.json"),
        )
    )


def compact(row):
    return {
        key: row[key]
        for key in (
            "max_levels",
            "actions",
            "status",
            "milestones",
            "source_counts",
            "transfer_issued_by_target",
            "transfer_trial_statuses",
            "matched_checkpoints_by_target",
            "capability_records",
            "capability_contract_records",
            "memory_format",
        )
    }


def batch() -> None:
    records = []
    for kind in ("fixture", "public"):
        manifest = json.loads((OUT / f"{kind}.json").read_text())
        for game in manifest["games"]:
            gid = game["game_id"]
            paired = {}
            for variant in VARIANTS:
                command = [
                    sys.executable,
                    __file__,
                    "cell",
                    "--kind",
                    kind,
                    "--game",
                    gid,
                    "--variant",
                    variant,
                ]
                done = subprocess.run(command, capture_output=True, text=True, timeout=50)
                if done.returncode:
                    raise RuntimeError(done.stderr[-3000:] + "\n" + done.stdout[-3000:])
                row = json.loads((OUT / f"{gid}-{variant}.json").read_text())
                assert row["status"] in ("WIN", "ACTION_BOUND"), row
                assert row["actions"] == len(row["trace"]) + 1
                paired[variant] = row
                print(
                    "REQUALIFICATION_CELL="
                    + json.dumps(
                        {key: value for key, value in row.items()
                         if key not in ("trace", "transfer_trial_records")},
                        sort_keys=True,
                    ),
                    flush=True,
                )
            assert len({row["initial_digest"] for row in paired.values()}) == 1
            records.append(
                {
                    "kind": kind,
                    "game_id": gid,
                    "variants": {variant: compact(row) for variant, row in paired.items()},
                }
            )
            write(
                OUT / "comparison.json",
                {
                    "prior_commit": PRIOR,
                    "interpretation": "public development diagnostic, not hidden generalization",
                    "complete": False,
                    "comparisons": records,
                },
            )

    fixture = next(row for row in records if row["kind"] == "fixture")["variants"]
    assert fixture["candidate"]["max_levels"] == 5
    assert fixture["candidate"]["status"] == "WIN"
    assert fixture["candidate"]["actions"] <= 73

    vc33 = next(row for row in records if row["game_id"].startswith("vc33-"))["variants"]
    assert vc33["candidate"]["max_levels"] >= 2
    assert vc33["candidate"]["actions"] <= 400

    report = {
        "prior_commit": PRIOR,
        "interpretation": "public development diagnostic, not hidden generalization",
        "trial_count": len(records) * len(VARIANTS),
        "complete": True,
        "comparisons": records,
    }
    write(OUT / "comparison.json", report)
    print("REQUALIFICATION_COMPARISON=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_CERTIFIED_REQUALIFICATION_QUALIFICATION=PASS", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "cell", "run"))
    parser.add_argument("--kind", choices=("fixture", "public"))
    parser.add_argument("--game")
    parser.add_argument("--variant", choices=VARIANTS)
    args = parser.parse_args()
    {"prepare": prepare, "cell": lambda: cell(args), "run": batch}[args.command]()
