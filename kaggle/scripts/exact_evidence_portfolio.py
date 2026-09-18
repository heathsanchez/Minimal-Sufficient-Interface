"""Exact-evidence portfolio compounding for ft09.

Generation 1 produced two complementary descendants:
  - compression-only explores a broad state frontier;
  - reinvestment spends quotient savings on fresh grounded interventions.

They currently repay for exact state-action consequences the sibling already
observed. This experiment banks and unions ONLY exact-context EffectMemory
evidence:
  (raw public context digest, exact action) -> observed target digest(s)
plus exact per-context catalogs.

No descriptor counts, affordance scores, visual factors, or inferred action
classes are shared. Conflicting targets are preserved and marked ambiguous.
Children then start with this exact evidence bank and the same Generation-1
quotient policy they would otherwise use.

The test asks whether "never pay twice for exact verified evidence" compounds
coverage inside the same 400-action budget.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from copy import deepcopy
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "exact-evidence-portfolio-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import action_quotient_reinvest as gen1

gen1.OUT = OUT
gen1.AGENT = AGENT
gen1.stable.OUT = OUT
gen1.stable.AGENT = AGENT
gen1.stable.aq.OUT = OUT
gen1.stable.aq.AGENT = AGENT
gen1.stable.transfer.OUT = OUT
gen1.stable.transfer.AGENT = AGENT

aq = gen1.stable.aq


def action_key(chosen, data):
    return (
        int(chosen.value),
        None if data.get("x") is None else int(data.get("x")),
        None if data.get("y") is None else int(data.get("y")),
    )


def export_exact_bank(effects):
    edges = {}
    for (context, action), row in effects.edges.items():
        edges[(str(context), tuple(action))] = {
            "n": int(row.get("n", 0)),
            "changed": int(row.get("changed", 0)),
            "outcomes": {
                str(target): int(count)
                for target, count in row.get("outcomes", {}).items()
            },
            "histories": [list(item) for item in row.get("histories", [])],
            "terminal": bool(row.get("terminal", False)),
            "ambiguous": bool(row.get("ambiguous", False)),
        }
    catalogs = {
        str(context): tuple(tuple(action) for action in actions)
        for context, actions in effects.catalogs.items()
    }
    return {"edges": edges, "catalogs": catalogs}


def merge_banks(*banks):
    merged_edges = {}
    merged_catalogs = {}

    for bank in banks:
        for key, row in bank["edges"].items():
            target = merged_edges.setdefault(
                key,
                {
                    "n": 0,
                    "changed": 0,
                    "outcomes": {},
                    "histories": [],
                    "terminal": False,
                    "ambiguous": False,
                },
            )
            target["n"] += int(row["n"])
            target["changed"] += int(row["changed"])
            for outcome, count in row["outcomes"].items():
                target["outcomes"][str(outcome)] = (
                    target["outcomes"].get(str(outcome), 0) + int(count)
                )
            for history in row.get("histories", []):
                history = list(history)
                if history not in target["histories"]:
                    target["histories"].append(history)
            target["histories"] = target["histories"][-8:]
            target["terminal"] = target["terminal"] or bool(row["terminal"])
            target["ambiguous"] = (
                target["ambiguous"]
                or bool(row["ambiguous"])
                or len(target["outcomes"]) > 1
            )

        for context, actions in bank["catalogs"].items():
            bucket = list(merged_catalogs.get(str(context), ()))
            seen = set(bucket)
            for action in actions:
                action = tuple(action)
                if action not in seen:
                    seen.add(action)
                    bucket.append(action)
            merged_catalogs[str(context)] = tuple(bucket)

    return {"edges": merged_edges, "catalogs": merged_catalogs}


def install_exact_bank(effects, bank, counters):
    effects.edges = OrderedDict()
    for key in sorted(bank["edges"], key=repr):
        effects.edges[key] = deepcopy(bank["edges"][key])
    effects.catalogs = OrderedDict(
        (context, tuple(actions))
        for context, actions in sorted(bank["catalogs"].items())
    )
    # Deliberately do not install descriptor statistics.
    effects.descriptors = OrderedDict()
    effects.total_observations = sum(
        int(row["n"]) for row in bank["edges"].values()
    )
    counters["preloaded_edge_keys"] = len(effects.edges)
    counters["preloaded_catalog_contexts"] = len(effects.catalogs)
    counters["preloaded_observations"] = effects.total_observations
    counters["preloaded_ambiguous_edges"] = sum(
        bool(row.get("ambiguous")) for row in effects.edges.values()
    )


def run_arm(
    module,
    game_id,
    envdir,
    max_actions,
    *,
    certified_states=None,
    classes=(),
    refill=False,
    preload_bank=None,
):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ft09 unavailable")

    policy = module.MyAgent(
        card_id="exact-evidence-portfolio",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    if certified_states:
        gen1.install_overlay(
            policy.controller,
            set(certified_states),
            classes,
            counters,
            refill=bool(refill),
        )
    if preload_bank is not None:
        install_exact_bank(policy.controller.effects, preload_bank, counters)

    initial_preloaded_keys = set(policy.controller.effects.edges)
    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    states = set()
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []
    preloaded_key_hits = 0

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        states.add(before_digest)
        before_level = int(before.levels_completed)

        # Count a real decision context where the bank already knows at least
        # one exact action consequence. This is evidence reuse, not a claim that
        # the chosen action itself will necessarily be banked.
        if any(context == before_digest for context, _action in initial_preloaded_keys):
            preloaded_key_hits += 1

        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key = action_key(chosen, data)
        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        after_digest = module.normalize_frame(latest).evidence_sha256
        states.add(after_digest)
        zero_change += int(before_digest == after_digest)
        actions.append(key)
        sources[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": len(actions) + 1})

        frames.append(latest)

    bank = export_exact_bank(policy.controller.effects)
    arc.close_scorecard()

    return {
        "actions_raw": actions,
        "states": states,
        "bank": bank,
        "stats": {
            "actions": len(actions) + 1,
            "unique_state_count": len(states),
            "distinct_actions": len(set(actions)),
            "distinct_action6": len({a for a in actions if a[0] == 6}),
            "zero_observation_change": zero_change,
            "max_levels": max_level,
            "milestones": milestones,
            "final_state": audit.state_name(latest),
            "source_counts": dict(sources),
            "bank_decision_context_hits": preloaded_key_hits,
            "exact_bank": {
                "edge_keys": len(bank["edges"]),
                "catalog_contexts": len(bank["catalogs"]),
                "ambiguous_edges": sum(
                    bool(row["ambiguous"]) for row in bank["edges"].values()
                ),
                "observations": sum(
                    int(row["n"]) for row in bank["edges"].values()
                ),
            },
            "overlay": dict(counters),
        },
    }


def bank_overlap(left, right):
    lkeys = set(left["edges"])
    rkeys = set(right["edges"])
    common = lkeys & rkeys
    conflicts = 0
    same = 0
    for key in common:
        lo = set(left["edges"][key]["outcomes"])
        ro = set(right["edges"][key]["outcomes"])
        if lo == ro:
            same += 1
        else:
            conflicts += 1
    return {
        "left_edge_keys": len(lkeys),
        "right_edge_keys": len(rkeys),
        "common_edge_keys": len(common),
        "same_target_sets": same,
        "conflicting_target_sets": conflicts,
        "union_edge_keys": len(lkeys | rkeys),
    }


def compact(row):
    return row["stats"]


def main():
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]

    module, prefixes, visits, protected, trace = aq.collect_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    selected, _rows, common, classes, _class_rows = (
        gen1.stable.derive_stable_classes(
            module,
            game_id,
            manifest["environments_dir"],
            prefixes,
            visits,
            protected,
        )
    )
    certified_states = {digest for _count, digest in selected}

    baseline = run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    compressed = run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        refill=False,
    )
    reinvested = run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        refill=True,
    )

    merged_bank = merge_banks(compressed["bank"], reinvested["bank"])
    overlap = bank_overlap(compressed["bank"], reinvested["bank"])

    child_compressed = run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        refill=False,
        preload_bank=merged_bank,
    )
    child_reinvested = run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        refill=True,
        preload_bank=merged_bank,
    )

    for row in (baseline, compressed, reinvested, child_compressed, child_reinvested):
        if row["stats"]["max_levels"] < 0:
            raise AssertionError("protected progress regressed")

    if overlap["conflicting_target_sets"] < 0:
        raise AssertionError("impossible overlap accounting")
    if len(merged_bank["edges"]) < max(
        len(compressed["bank"]["edges"]),
        len(reinvested["bank"]["edges"]),
    ):
        raise AssertionError("merged exact bank lost evidence")
    if (
        child_compressed["stats"]["bank_decision_context_hits"]
        + child_reinvested["stats"]["bank_decision_context_hits"]
        < 1
    ):
        raise AssertionError("exact portfolio bank was never encountered")

    parent_union = compressed["states"] | reinvested["states"]
    child_union = child_compressed["states"] | child_reinvested["states"]
    all_union = baseline["states"] | parent_union | child_union

    report = {
        "interpretation": (
            "portfolio compounding by sharing only exact raw-context/action "
            "consequence evidence between compression and reinvestment siblings"
        ),
        "claim_boundary": (
            "only EffectMemory exact edges and exact catalogs are preloaded; "
            "descriptor statistics and AffordanceMemory are deliberately excluded; "
            "conflicting target sets remain ambiguous"
        ),
        "prior_commit": "c7fa8966b9ca7bd9e86d6392c068aafa50a5524d",
        "game_id": game_id,
        "trace": trace,
        "gen1_common_action_count": len(common),
        "gen1_class_sizes": [len(group) for group in classes],
        "bank_overlap": overlap,
        "merged_bank": {
            "edge_keys": len(merged_bank["edges"]),
            "catalog_contexts": len(merged_bank["catalogs"]),
            "ambiguous_edges": sum(
                bool(row["ambiguous"]) for row in merged_bank["edges"].values()
            ),
            "observations": sum(
                int(row["n"]) for row in merged_bank["edges"].values()
            ),
        },
        "parents": {
            "baseline": compact(baseline),
            "compressed": compact(compressed),
            "reinvested": compact(reinvested),
            "parent_union_states": len(parent_union),
            "parent_union_novel_vs_baseline": len(parent_union - baseline["states"]),
        },
        "children": {
            "compressed_with_portfolio": compact(child_compressed),
            "reinvested_with_portfolio": compact(child_reinvested),
            "child_union_states": len(child_union),
            "child_union_novel_vs_parents": len(child_union - parent_union),
            "child_union_novel_vs_baseline": len(child_union - baseline["states"]),
        },
        "compounding": {
            "total_evidence_union_states": len(all_union),
            "baseline_states": len(baseline["states"]),
            "state_evidence_multiplier": (
                len(all_union) / max(1, len(baseline["states"]))
            ),
            "new_states_beyond_parent_union": len(
                child_union - (baseline["states"] | parent_union)
            ),
        },
    }

    audit.write_json(OUT / "exact-evidence-portfolio.json", report)
    print(
        "EXACT_EVIDENCE_PORTFOLIO_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_EXACT_EVIDENCE_PORTFOLIO=PASS", flush=True)


if __name__ == "__main__":
    main()
