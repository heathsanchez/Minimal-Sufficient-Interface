"""Source-blind resource-dominance diagnostic on frozen MG-ARC9."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "resource-dominance-results"
AGENT = OUT / "agent.py"


def run_world(game_id: str, envdir: str, max_actions: int) -> dict:
    from arc_agi import Arcade, OperationMode

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()
    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline world unavailable")
    policy = module.MyAgent(
        card_id="resource-dominance",
        game_id="source-blind",
        agent_name="frozen",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    c = policy.controller
    c.archived_capabilities = ()

    visits = []
    best_quality: dict[str, int] = {}
    resource_values: dict[str, set[int]] = defaultdict(set)
    original_select = c._select_probe

    def measured_select(obs, catalog):
        active = bool(
            c.border_factor_enabled
            and c._grid
            and c.border_factor.active(
                obs.levels_completed, len(c._grid), len(c._grid[0])
            )
        )
        snapshot = None
        if active:
            world = c._consequence_context(obs, c._grid)
            sig = c._resource_signature(obs, c._grid)
            if sig:
                color, value, direction = (int(sig[0]), int(sig[1]), int(sig[2]))
                quality = -direction * value
                old = best_quality.get(world)
                dominated = old is not None and quality < old
                if old is None or quality > old:
                    best_quality[world] = quality
                resource_values[world].add(value)
                effects = c.world_effects
                allowed = {c._action_key(t) for t in catalog}
                current_untried = sum(
                    effects.attempts(world, c._action_key(t)) == 0
                    for t in catalog
                )
                reachable = effects.frontier_action(world)
                snapshot = {
                    "world": world,
                    "color": color,
                    "resource": value,
                    "direction": direction,
                    "quality": quality,
                    "previous_best_quality": old,
                    "dominated": dominated,
                    "current_untried": current_untried,
                    "reachable_frontier": reachable in allowed if reachable is not None else False,
                }
        token = original_select(obs, catalog)
        if snapshot is not None:
            snapshot["selected_source"] = token.source
            snapshot["selected_action"] = list(c._action_key(token))
            visits.append(snapshot)
        return token

    c._select_probe = measured_select
    result = audit.run_session(
        policy,
        env,
        lambda observation: module.normalize_frame(observation).evidence_sha256,
        max_actions=max_actions,
        wall_seconds=35,
    )
    arc.close_scorecard()

    dominated = [v for v in visits if v["dominated"]]
    nondominated = [v for v in visits if not v["dominated"]]
    multi = {w: sorted(vals) for w, vals in resource_values.items() if len(vals) > 1}
    frontier_dominated = [v for v in dominated if v["selected_source"] == "consequence_frontier"]
    frontier_nondominated = [v for v in nondominated if v["selected_source"] == "consequence_frontier"]
    dominated_with_untried = [v for v in dominated if v["current_untried"] > 0]

    return {
        "game_id": game_id,
        "actions": result["actions"],
        "status": result["status"],
        "max_levels": result["max_levels"],
        "milestones": result["milestones"],
        "factor_active": bool(visits),
        "factor_visits": len(visits),
        "world_states_seen": len(resource_values),
        "world_states_with_multiple_resource_values": len(multi),
        "multi_resource_examples": dict(list(sorted(multi.items()))[:12]),
        "dominated_visits": len(dominated),
        "dominated_visit_fraction": len(dominated) / max(1, len(visits)),
        "dominated_frontier_actions": len(frontier_dominated),
        "nondominated_frontier_actions": len(frontier_nondominated),
        "dominated_visits_with_current_untried_actions": len(dominated_with_untried),
        "dominated_source_counts": dict(Counter(v["selected_source"] for v in dominated)),
        "nondominated_source_counts": dict(Counter(v["selected_source"] for v in nondominated)),
        "max_resource_levels_per_world": max((len(v) for v in resource_values.values()), default=0),
        "source_counts": result["source_counts"],
    }


def main() -> None:
    manifests = {
        kind: json.loads((OUT / f"{kind}.json").read_text())
        for kind in ("fixture", "public")
    }
    worlds = []
    for kind, manifest in manifests.items():
        for row in manifest["games"]:
            worlds.append(
                run_world(
                    row["game_id"],
                    manifest["environments_dir"],
                    manifest["max_actions"],
                )
            )
    report = {
        "interpretation": "source-blind resource-dominance diagnostic",
        "agent_sha256": audit.sha(AGENT.read_bytes()),
        "worlds": worlds,
    }
    audit.write_json(OUT / "resource-dominance-diagnostic.json", report)
    print("RESOURCE_DOMINANCE_DIAGNOSTIC=" + json.dumps(report, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
