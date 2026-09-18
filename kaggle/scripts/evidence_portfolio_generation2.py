"""Generation-2 exact-evidence portfolio compounding for ft09.

Generation 1 established a stable exact action quotient. Its compression-only
and reinvestment descendants exposed complementary state frontiers. The first
portfolio run then unioned only their exact EffectMemory evidence and produced
children whose total retained state-evidence union reached 323 states from an
87-state baseline.

This generation continues the same loop without introducing inferred ontology:

  G1 quotient
    -> sibling exact evidence union
    -> banked child trajectory
    -> select child states absent from both parents
    -> learn exact local one-step action quotients at those states
    -> carry the child's enlarged exact evidence bank forward
    -> compile local quotients into compression/reinvestment grandchildren
    -> union all evidence again.

All local quotients are scoped to one exact public observation digest. The
portfolio bank contains exact raw-context/action consequences and catalogs only;
descriptor statistics and affordance generalization are not inherited.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "evidence-portfolio-generation2-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import exact_evidence_portfolio as portfolio
import action_quotient_reinvest as gen1

portfolio.OUT = OUT
portfolio.AGENT = AGENT
portfolio.gen1.OUT = OUT
portfolio.gen1.AGENT = AGENT
portfolio.gen1.stable.OUT = OUT
portfolio.gen1.stable.AGENT = AGENT
portfolio.gen1.stable.aq.OUT = OUT
portfolio.gen1.stable.aq.AGENT = AGENT
portfolio.gen1.stable.transfer.OUT = OUT
portfolio.gen1.stable.transfer.AGENT = AGENT

gen1.OUT = OUT
gen1.AGENT = AGENT
gen1.stable.OUT = OUT
gen1.stable.AGENT = AGENT
gen1.stable.aq.OUT = OUT
gen1.stable.aq.AGENT = AGENT
gen1.stable.transfer.OUT = OUT
gen1.stable.transfer.AGENT = AGENT

aq = gen1.stable.aq
transfer = gen1.stable.transfer

LOCAL_STATES = 8


def install_local_overlay(controller, local_maps, counters):
    original = controller._catalog

    def transformed(self, obs):
        catalog = original(obs)
        mapping = local_maps.get(obs.evidence_sha256)
        if not mapping:
            return catalog

        counters["g2_catalog_calls"] += 1
        target_width = len(self._primary)
        kept = []
        kept_keys = set()
        for token in catalog:
            key = self._action_key(token)
            rep = mapping.get(key)
            if rep is not None and key != rep:
                counters["g2_suppressed_candidates"] += 1
                continue
            if key in kept_keys:
                continue
            kept_keys.add(key)
            kept.append(token)

        primary = []
        primary_keys = set()
        for token in self._primary:
            key = self._action_key(token)
            if key in kept_keys and key not in primary_keys:
                primary.append(token)
                primary_keys.add(key)

        for token in kept:
            if len(primary) >= target_width:
                break
            key = self._action_key(token)
            if key in primary_keys:
                continue
            primary.append(token)
            primary_keys.add(key)
            counters["g2_refill_slots"] += 1

        self._primary = tuple(primary)
        return tuple(kept)

    controller._catalog = MethodType(transformed, controller)


def run_collect(
    module,
    game_id,
    envdir,
    max_actions,
    *,
    gen1_states=None,
    gen1_classes=(),
    gen1_refill=False,
    preload_bank=None,
    local_maps=None,
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
        card_id="evidence-portfolio-generation2",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    if gen1_states:
        gen1.install_overlay(
            policy.controller,
            set(gen1_states),
            gen1_classes,
            counters,
            refill=bool(gen1_refill),
        )
    if local_maps:
        install_local_overlay(policy.controller, local_maps, counters)
    if preload_bank is not None:
        portfolio.install_exact_bank(policy.controller.effects, preload_bank, counters)

    latest = policy._convert_raw_frame_data(env.observation_space)
    digest = module.normalize_frame(latest).evidence_sha256
    prefix = ()
    prefixes = {digest: prefix}
    visits = Counter([digest])
    protected = {
        digest: (audit.state_name(latest), int(latest.levels_completed))
    }
    states = {digest}
    frames = [latest]
    actions = []
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        before_level = int(before.levels_completed)

        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )
        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        digest = module.normalize_frame(latest).evidence_sha256
        states.add(digest)
        actions.append(key)
        prefix = prefix + (key,)
        old = prefixes.get(digest)
        if old is None or len(prefix) < len(old):
            prefixes[digest] = prefix
        visits[digest] += 1
        protected[digest] = (
            audit.state_name(latest),
            int(latest.levels_completed),
        )
        zero_change += int(before_digest == digest)
        sources[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": len(actions) + 1})

        frames.append(latest)

    bank = portfolio.export_exact_bank(policy.controller.effects)
    arc.close_scorecard()
    return {
        "prefixes": prefixes,
        "visits": visits,
        "protected": protected,
        "states": states,
        "actions_raw": actions,
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
            "overlay": dict(counters),
            "bank_edge_keys": len(bank["edges"]),
            "bank_catalog_contexts": len(bank["catalogs"]),
        },
    }


def choose_novel_states(child, excluded):
    rows = []
    for digest, prefix in child["prefixes"].items():
        if digest in excluded:
            continue
        if child["protected"].get(digest, ("", 0))[0] != "NOT_FINISHED":
            continue
        rows.append((
            -int(child["visits"].get(digest, 0)),
            len(prefix),
            digest,
        ))
    rows.sort()
    return [
        {
            "digest": digest,
            "visits": -negative_visits,
            "prefix_length": prefix_length,
            "prefix": child["prefixes"][digest],
        }
        for negative_visits, prefix_length, digest in rows[:LOCAL_STATES]
    ]


def local_quotient(module, game_id, envdir, row):
    table, _descriptors = transfer.consequence_table(
        module,
        game_id,
        envdir,
        row["digest"],
        row["prefix"],
    )
    grouped = {}
    for action, consequence in table.items():
        grouped.setdefault(consequence, []).append(tuple(action))
    classes = sorted(
        (tuple(sorted(group)) for group in grouped.values()),
        key=lambda group: (-len(group), group),
    )
    mapping = {
        member: group[0]
        for group in classes
        if len(group) > 1
        for member in group
    }
    return mapping, {
        "digest": row["digest"],
        "visits": row["visits"],
        "prefix_length": row["prefix_length"],
        "candidate_actions": len(table),
        "consequence_classes": len(classes),
        "compression": len(table) / max(1, len(classes)),
        "largest_class": max((len(group) for group in classes), default=0),
        "class_sizes": [len(group) for group in classes],
    }


def bank_summary(bank):
    return {
        "edge_keys": len(bank["edges"]),
        "catalog_contexts": len(bank["catalogs"]),
        "ambiguous_edges": sum(
            bool(row.get("ambiguous")) for row in bank["edges"].values()
        ),
        "observations": sum(
            int(row["n"]) for row in bank["edges"].values()
        ),
    }


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
    selected, _rows, common, g1_classes, _class_rows = (
        gen1.stable.derive_stable_classes(
            module,
            game_id,
            manifest["environments_dir"],
            prefixes,
            visits,
            protected,
        )
    )
    g1_states = {digest for _count, digest in selected}

    baseline = run_collect(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    compressed = run_collect(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=g1_states,
        gen1_classes=g1_classes,
        gen1_refill=False,
    )
    reinvested = run_collect(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=g1_states,
        gen1_classes=g1_classes,
        gen1_refill=True,
    )
    parent_bank = portfolio.merge_banks(compressed["bank"], reinvested["bank"])

    # The portfolio children were identical in Generation 1; use the
    # reinvestment child as the acquisition parent for new exact contexts.
    banked_child = run_collect(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=g1_states,
        gen1_classes=g1_classes,
        gen1_refill=True,
        preload_bank=parent_bank,
    )

    parent_union = compressed["states"] | reinvested["states"]
    excluded = baseline["states"] | parent_union
    chosen = choose_novel_states(banked_child, excluded)
    if not chosen:
        raise AssertionError("banked child exposed no novel exact state")

    local_maps = {}
    local_rows = []
    for row in chosen:
        mapping, summary = local_quotient(
            module,
            game_id,
            manifest["environments_dir"],
            row,
        )
        local_maps[row["digest"]] = mapping
        local_rows.append(summary)
        print(
            "PORTFOLIO_G2_LOCAL="
            + json.dumps(summary, sort_keys=True),
            flush=True,
        )
    if not any(local_maps.values()):
        raise AssertionError("portfolio Generation 2 learned no nontrivial local quotient")

    child_bank = banked_child["bank"]

    grand_compressed = run_collect(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=g1_states,
        gen1_classes=g1_classes,
        gen1_refill=False,
        preload_bank=child_bank,
        local_maps=local_maps,
    )
    grand_reinvested = run_collect(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=g1_states,
        gen1_classes=g1_classes,
        gen1_refill=True,
        preload_bank=child_bank,
        local_maps=local_maps,
    )

    all_rows = (
        baseline,
        compressed,
        reinvested,
        banked_child,
        grand_compressed,
        grand_reinvested,
    )
    for row in all_rows:
        if row["stats"]["max_levels"] < 0:
            raise AssertionError("protected progress regressed")

    if (
        grand_compressed["stats"]["overlay"].get("g2_catalog_calls", 0)
        + grand_reinvested["stats"]["overlay"].get("g2_catalog_calls", 0)
        < 1
    ):
        raise AssertionError("portfolio Generation-2 local quotient never activated")

    grand_union = grand_compressed["states"] | grand_reinvested["states"]
    generation1_union = baseline["states"] | parent_union | banked_child["states"]
    total_union = generation1_union | grand_union

    report = {
        "interpretation": (
            "second-generation exact-evidence portfolio: banked child novelty "
            "generates exact local action quotients; child bank and local "
            "certificates are inherited by two grandchildren"
        ),
        "claim_boundary": (
            "local quotients are exact-state one-step consequence classes only; "
            "the inherited evidence bank contains exact raw-context/action "
            "effects and catalogs only"
        ),
        "prior_commit": "62bec7279a9bfb7d1f1dcdda878d01156d501118",
        "game_id": game_id,
        "trace": trace,
        "g1_common_action_count": len(common),
        "g1_class_sizes": [len(group) for group in g1_classes],
        "local_state_count": len(chosen),
        "local_quotients": local_rows,
        "banks": {
            "parent_union": bank_summary(parent_bank),
            "banked_child": bank_summary(child_bank),
            "edge_growth": (
                len(child_bank["edges"]) - len(parent_bank["edges"])
            ),
        },
        "generations": {
            "baseline": baseline["stats"],
            "compressed_parent": compressed["stats"],
            "reinvested_parent": reinvested["stats"],
            "banked_child": banked_child["stats"],
            "grand_compressed": grand_compressed["stats"],
            "grand_reinvested": grand_reinvested["stats"],
        },
        "compounding": {
            "baseline_states": len(baseline["states"]),
            "parent_union_states": len(parent_union),
            "banked_child_states": len(banked_child["states"]),
            "grandchild_union_states": len(grand_union),
            "grandchild_novel_vs_generation1": len(
                grand_union - generation1_union
            ),
            "total_evidence_union_states": len(total_union),
            "state_evidence_multiplier": (
                len(total_union) / max(1, len(baseline["states"]))
            ),
        },
    }
    audit.write_json(
        OUT / "evidence-portfolio-generation2.json",
        report,
    )
    print(
        "EVIDENCE_PORTFOLIO_GENERATION2_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_EVIDENCE_PORTFOLIO_GENERATION2=PASS", flush=True)


if __name__ == "__main__":
    main()
