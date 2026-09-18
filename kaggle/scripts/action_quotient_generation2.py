"""Generation-2 ft09 quotient compounding.

Generation 1 proved two exact action classes (50 and 5 members) across twelve
recurrent states. Compression/reinvestment then exposed a much larger evidence
frontier: the compression and refill descendants together see far more states
than the frozen baseline.

This experiment banks that descendant evidence instead of choosing a winner.
It learns exact *local* one-step action quotients on novel descendant states,
then replays each parent policy with those newly certified state-scoped action
classes compiled in.  Every Generation-2 quotient is exact-state scoped; no
cross-state transfer is assumed.

The loop is:
  G1 certificate -> new states -> local G2 certificates -> compile -> new states.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "action-quotient-generation2-results"
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
transfer = gen1.stable.transfer

PER_PARENT_STATES = 6


def action_key(chosen, data):
    return (
        int(chosen.value),
        None if data.get("x") is None else int(data.get("x")),
        None if data.get("y") is None else int(data.get("y")),
    )


def collect_parent(
    module,
    game_id,
    envdir,
    max_actions,
    *,
    certified_states=None,
    classes=(),
    refill=False,
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
        card_id="action-quotient-generation2-parent",
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

    latest = policy._convert_raw_frame_data(env.observation_space)
    digest = module.normalize_frame(latest).evidence_sha256
    prefix = ()
    prefixes = {digest: prefix}
    visits = Counter([digest])
    protected = {
        digest: (audit.state_name(latest), int(latest.levels_completed))
    }
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
        key = action_key(chosen, data)
        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        digest = module.normalize_frame(latest).evidence_sha256

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

    arc.close_scorecard()
    return {
        "prefixes": prefixes,
        "visits": visits,
        "protected": protected,
        "actions_raw": actions,
        "stats": {
            "actions": len(actions) + 1,
            "unique_state_count": len(prefixes),
            "distinct_actions": len(set(actions)),
            "distinct_action6": len({a for a in actions if a[0] == 6}),
            "zero_observation_change": zero_change,
            "max_levels": max_level,
            "milestones": milestones,
            "final_state": audit.state_name(latest),
            "source_counts": dict(sources),
            "overlay": dict(counters),
        },
    }


def select_novel_states(parent, baseline_states, used, label, limit):
    candidates = []
    for digest, prefix in parent["prefixes"].items():
        if digest in baseline_states or digest in used:
            continue
        if parent["protected"].get(digest, ("", 0))[0] != "NOT_FINISHED":
            continue
        candidates.append((
            -int(parent["visits"].get(digest, 0)),
            len(prefix),
            digest,
        ))
    candidates.sort()

    rows = []
    for _neg_visits, prefix_length, digest in candidates[:limit]:
        used.add(digest)
        rows.append({
            "digest": digest,
            "parent": label,
            "visits": int(parent["visits"].get(digest, 0)),
            "prefix_length": prefix_length,
            "prefix": parent["prefixes"][digest],
        })
    return rows


def local_quotient(module, game_id, envdir, row):
    table, _descriptors = transfer.consequence_table(
        module,
        game_id,
        envdir,
        row["digest"],
        row["prefix"],
    )
    groups = defaultdict(list)
    for action, consequence in table.items():
        groups[consequence].append(tuple(action))

    classes = sorted(
        (tuple(sorted(group)) for group in groups.values()),
        key=lambda group: (-len(group), group),
    )
    mapping = {
        member: group[0]
        for group in classes
        if len(group) > 1
        for member in group
    }
    return {
        "digest": row["digest"],
        "parent": row["parent"],
        "visits": row["visits"],
        "prefix_length": row["prefix_length"],
        "candidate_actions": len(table),
        "consequence_classes": len(classes),
        "compression": len(table) / max(1, len(classes)),
        "largest_class": max((len(group) for group in classes), default=0),
        "class_sizes": [len(group) for group in classes],
        "mapping": mapping,
        "classes": classes,
    }


def gen1_member_map(classes):
    return {
        member: group[0]
        for group in classes
        if len(group) > 1
        for member in group
    }


def install_generation2_overlay(
    controller,
    gen1_states,
    gen1_classes,
    local_maps,
    counters,
    *,
    gen1_refill,
):
    original = controller._catalog
    first_map = gen1_member_map(gen1_classes)

    def transformed(self, obs):
        catalog = original(obs)
        digest = obs.evidence_sha256
        mapping = {}

        if digest in gen1_states:
            counters["g1_calls"] += 1
            mapping.update(first_map)

        local = local_maps.get(digest)
        if local:
            counters["g2_calls"] += 1
            mapping.update(local)

        if not mapping:
            return catalog

        original_primary = tuple(self._primary)
        target_width = len(original_primary)
        original_primary_keys = {
            self._action_key(token) for token in original_primary
        }

        kept = []
        kept_keys = set()
        for token in catalog:
            key = self._action_key(token)
            rep = mapping.get(key)
            if rep is not None and key != rep:
                counters["suppressed_candidates"] += 1
                if local and key in local:
                    counters["g2_suppressed_candidates"] += 1
                continue
            if key in kept_keys:
                continue
            kept_keys.add(key)
            kept.append(token)

        primary = []
        primary_keys = set()
        for token in original_primary:
            key = self._action_key(token)
            if key not in kept_keys or key in primary_keys:
                continue
            primary.append(token)
            primary_keys.add(key)

        # Generation-2 savings are always reinvested.  Generation-1 can follow
        # either its compression-only or refill parent behavior until G2 fires.
        should_refill = bool(local) or (digest in gen1_states and gen1_refill)
        if should_refill:
            for token in kept:
                if len(primary) >= target_width:
                    break
                key = self._action_key(token)
                if key in primary_keys:
                    continue
                primary.append(token)
                primary_keys.add(key)
                counters["refill_slots"] += 1
                if key not in original_primary_keys:
                    counters["novel_primary_candidates"] += 1

        self._primary = tuple(primary)
        counters["catalog_entries_before"] += len(catalog)
        counters["catalog_entries_after"] += len(kept)
        return tuple(kept)

    controller._catalog = MethodType(transformed, controller)


def run_generation2(
    module,
    game_id,
    envdir,
    max_actions,
    *,
    gen1_states,
    gen1_classes,
    local_maps,
    gen1_refill,
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
        card_id="action-quotient-generation2-child",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    install_generation2_overlay(
        policy.controller,
        set(gen1_states),
        gen1_classes,
        local_maps,
        counters,
        gen1_refill=gen1_refill,
    )

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    states = set()
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        states.add(before_digest)
        before_level = int(before.levels_completed)

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

    arc.close_scorecard()
    return {
        "actions_raw": actions,
        "states": states,
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
        },
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
    selected, _state_rows, common, gen1_classes, _class_rows = (
        gen1.stable.derive_stable_classes(
            module,
            game_id,
            manifest["environments_dir"],
            prefixes,
            visits,
            protected,
        )
    )
    gen1_states = {digest for _count, digest in selected}

    baseline = collect_parent(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    compressed = collect_parent(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=gen1_states,
        classes=gen1_classes,
        refill=False,
    )
    reinvested = collect_parent(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=gen1_states,
        classes=gen1_classes,
        refill=True,
    )

    baseline_states = set(baseline["prefixes"])
    used = set()
    chosen = []
    chosen += select_novel_states(
        compressed, baseline_states, used, "compressed", PER_PARENT_STATES
    )
    chosen += select_novel_states(
        reinvested, baseline_states, used, "reinvested", PER_PARENT_STATES
    )
    if not chosen:
        raise AssertionError("Generation 1 exposed no novel states")

    local_rows = []
    local_maps = {}
    for row in chosen:
        learned = local_quotient(
            module,
            game_id,
            manifest["environments_dir"],
            row,
        )
        local_rows.append({
            key: value
            for key, value in learned.items()
            if key not in ("mapping", "classes")
        })
        local_maps[row["digest"]] = learned["mapping"]
        print(
            "ACTION_QUOTIENT_G2_STATE="
            + json.dumps(local_rows[-1], sort_keys=True),
            flush=True,
        )

    if not any(local_maps.values()):
        raise AssertionError("Generation 2 learned no nontrivial local action class")

    child_compressed = run_generation2(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=gen1_states,
        gen1_classes=gen1_classes,
        local_maps=local_maps,
        gen1_refill=False,
    )
    child_reinvested = run_generation2(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        gen1_states=gen1_states,
        gen1_classes=gen1_classes,
        local_maps=local_maps,
        gen1_refill=True,
    )

    for row in (baseline, compressed, reinvested):
        if row["stats"]["max_levels"] != 0:
            raise AssertionError("ft09 parent baseline changed")
    for row in (child_compressed, child_reinvested):
        if row["stats"]["max_levels"] < 0:
            raise AssertionError("Generation 2 regressed protected progress")

    if (
        child_compressed["stats"]["overlay"].get("g2_calls", 0)
        + child_reinvested["stats"]["overlay"].get("g2_calls", 0)
        < 1
    ):
        raise AssertionError("Generation 2 quotient never activated")

    parent_union = (
        set(compressed["prefixes"]) | set(reinvested["prefixes"])
    )
    child_union = child_compressed["states"] | child_reinvested["states"]
    all_union = baseline_states | parent_union | child_union

    report = {
        "interpretation": (
            "Generation-2 exact-state action quotienting learned from the union "
            "of compression and reinvestment descendants; local certificates are "
            "compiled back into both parent policies and their savings refilled"
        ),
        "claim_boundary": (
            "Generation-2 classes are exact one-step consequence classes at the "
            "selected public state only; no visual or cross-state generalization"
        ),
        "prior_commit": "c7fa8966b9ca7bd9e86d6392c068aafa50a5524d",
        "game_id": game_id,
        "trace": trace,
        "gen1_common_action_count": len(common),
        "gen1_class_sizes": [len(group) for group in gen1_classes],
        "generation2_state_count": len(chosen),
        "generation2_states": local_rows,
        "parents": {
            "baseline": baseline["stats"],
            "compressed": compressed["stats"],
            "reinvested": reinvested["stats"],
            "baseline_unique_states": len(baseline_states),
            "parent_union_unique_states": len(parent_union),
            "parent_union_novel_vs_baseline": len(parent_union - baseline_states),
        },
        "children": {
            "from_compressed": child_compressed["stats"],
            "from_reinvested": child_reinvested["stats"],
            "child_union_unique_states": len(child_union),
            "child_union_novel_vs_parents": len(child_union - parent_union),
            "child_union_novel_vs_baseline": len(child_union - baseline_states),
        },
        "compounding": {
            "total_evidence_union_states": len(all_union),
            "baseline_states": len(baseline_states),
            "state_evidence_multiplier": len(all_union) / max(1, len(baseline_states)),
            "new_states_beyond_generation1_union": len(
                child_union - (baseline_states | parent_union)
            ),
        },
    }

    audit.write_json(
        OUT / "action-quotient-generation2.json",
        report,
    )
    print(
        "ACTION_QUOTIENT_GENERATION2_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_ACTION_QUOTIENT_GENERATION2=PASS", flush=True)


if __name__ == "__main__":
    main()
