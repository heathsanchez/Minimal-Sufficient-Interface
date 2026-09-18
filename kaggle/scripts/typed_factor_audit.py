"""Matched typed-factor diagnostic against qualified MG-ARC5.

The factor may only affect consequence-state identity. Exact .mg contexts,
certified transfer guards, refutations and capability records remain raw.
Public worlds are development diagnostics, not sealed holdouts.
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
OUT = ROOT / "kaggle" / "typed-factor-results"
PRIOR = "07fe94a80edfbb295049d4140aef14ef2b47524b"
PRIOR_AGENT_SHA = "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead"
GAMES = {
    "ft09-0d8bbf25": "aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783",
    "ls20-9607627b": "298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92",
    "vc33-5430563c": "8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd",
}
VARIANTS = ("candidate", "prior", "no_typed_factor")
audit.BASELINE = PRIOR


def agent_path(variant):
    return OUT / ("prior.py" if variant == "prior" else "candidate.py")


def prepare():
    assert audit.sha(agent_path("prior").read_bytes()) == PRIOR_AGENT_SHA
    audit.AGENT = agent_path("candidate")
    for kind in ("fixture", "public"):
        path = OUT / f"{kind}.json"
        args = SimpleNamespace(
            fixtures=kind == "fixture",
            games="bt11" if kind == "fixture" else "ft09,ls20,vc33",
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
        manifest["seeds"] = [0]
        manifest["baseline_commit"] = PRIOR
        manifest["interpretation"] = "public development diagnostic, not hidden generalization"
        if kind == "public":
            assert {row["game_id"] for row in manifest["games"]} == set(GAMES)
            for row in manifest["games"]:
                filename = row["game_id"].split("-")[0] + ".py"
                assert row["files"][filename] == GAMES[row["game_id"]]
        audit.write_json(path, manifest)
    print("ARC3_TYPED_FACTOR_MANIFESTS=PASS", flush=True)


def cell(args):
    manifest = json.loads((OUT / f"{args.kind}.json").read_text())
    audit.AGENT = agent_path(args.variant)
    manifest["generated_agent_sha256"] = audit.sha(audit.AGENT.read_bytes())
    path = OUT / f"{args.kind}-{args.variant}-manifest.json"
    audit.write_json(path, manifest)

    old_session = audit.run_session

    def measured(policy, env, digest, **kwargs):
        policy.controller.archived_capabilities = ()
        if args.variant == "no_typed_factor":
            policy.controller.typed_factor_enabled = False
        result = old_session(policy, env, digest, **kwargs)
        controller = policy.controller
        factor = getattr(controller, "typed_factor", None)
        effects = getattr(controller, "effects", None)
        contexts = set()
        world_contexts = set()
        if effects is not None:
            for (source, _action), row in effects.edges.items():
                contexts.add(str(source))
                contexts.update(str(target) for target in row.get("outcomes", {}))
            contexts.update(str(key) for key in effects.catalogs)
            world_contexts = {key for key in contexts if key.startswith("w:")}

        factors = []
        if factor is not None:
            # Access is diagnostic-only; the public policy never sees world IDs.
            for (level, height, width), row in sorted(factor._factors.items()):
                factors.append({
                    "level": level,
                    "height": height,
                    "width": width,
                    "side": row["side"],
                    "depth": row["depth"],
                    "palette": list(row["palette"]),
                    "compression": row["compression"],
                })
        result.update(
            variant=args.variant,
            controller=type(controller).__name__,
            prior_commit=PRIOR,
            typed_factor_enabled=bool(getattr(controller, "typed_factor_enabled", False)),
            typed_active_contexts=int(getattr(factor, "active_contexts", 0) if factor else 0),
            typed_factors=factors,
            typed_scalar_transitions=len(factor.transitions()) if factor else 0,
            learned_effect_contexts=len(contexts),
            learned_world_contexts=len(world_contexts),
        )
        return result

    audit.run_session = measured
    audit.cell(SimpleNamespace(
        manifest=str(path),
        game=args.game,
        seed=0,
        arm="full",
        output=str(OUT / f"{args.game}-{args.variant}.json"),
    ))


def compact(row):
    return {key: row[key] for key in (
        "max_levels", "actions", "status", "milestones", "source_counts",
        "capability_records", "distinct_observations", "terminal_failures",
        "typed_factor_enabled", "typed_active_contexts", "typed_factors",
        "typed_scalar_transitions", "learned_effect_contexts",
        "learned_world_contexts", "memory_digest",
    )}


def batch():
    records = []
    for kind in ("fixture", "public"):
        manifest = json.loads((OUT / f"{kind}.json").read_text())
        for game in manifest["games"]:
            gid = game["game_id"]
            paired = {}
            for variant in VARIANTS:
                done = subprocess.run([
                    sys.executable, __file__, "cell",
                    "--kind", kind, "--game", gid, "--variant", variant,
                ], capture_output=True, text=True, timeout=50)
                if done.returncode:
                    raise RuntimeError(done.stderr[-3000:] + "\n" + done.stdout[-3000:])
                row = json.loads((OUT / f"{gid}-{variant}.json").read_text())
                assert row["status"] in ("WIN", "ACTION_BOUND"), row
                assert row["actions"] == len(row["trace"]) + 1
                paired[variant] = row
                print(
                    "TYPED_FACTOR_CELL="
                    + json.dumps({k:v for k,v in row.items() if k != "trace"}, sort_keys=True),
                    flush=True,
                )
            assert len({row["initial_digest"] for row in paired.values()}) == 1
            records.append({
                "kind": kind,
                "game_id": gid,
                "variants": {name: compact(row) for name,row in paired.items()},
            })
            audit.write_json(OUT / "comparison.json", {
                "prior_commit": PRIOR,
                "interpretation": "public development diagnostic, not hidden generalization",
                "complete": False,
                "comparisons": records,
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

    report = {
        "prior_commit": PRIOR,
        "interpretation": "public development diagnostic, not hidden generalization",
        "trial_count": len(records) * len(VARIANTS),
        "complete": True,
        "comparisons": records,
    }
    audit.write_json(OUT / "comparison.json", report)
    print("TYPED_FACTOR_COMPARISON=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_TYPED_FACTOR_QUALIFICATION=PASS", flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("prepare","cell","run"))
    p.add_argument("--kind",choices=("fixture","public"))
    p.add_argument("--game")
    p.add_argument("--variant",choices=VARIANTS)
    args=p.parse_args()
    {"prepare":prepare,"cell":lambda:cell(args),"run":batch}[args.command]()
