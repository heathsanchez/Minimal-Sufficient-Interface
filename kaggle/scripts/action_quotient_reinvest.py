"""Reinvest certified ft09 action-quotient savings into new intervention coverage.

The stable-core gate proved that 63 grounded actions collapse to ten exact
one-step consequence classes on twelve recurrent public states, with nontrivial
classes of size 50 and 5. The first operational compile merely removed redundant
members. This experiment spends that saved candidate capacity immediately:

  1. keep one representative from every certified action class;
  2. remove only certified redundant members at the twelve exact states;
  3. refill the original primary frontier width with later grounded candidates
     from the unchanged frozen controller catalog;
  4. leave every other state and every raw evidence/verifier path unchanged.

The question is whether certified compression buys more novel intervention and
state coverage inside the same 400-action budget.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "action-quotient-reinvest-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import action_quotient_stable_core as stable

stable.OUT = OUT
stable.AGENT = AGENT
stable.aq.OUT = OUT
stable.aq.AGENT = AGENT
stable.transfer.OUT = OUT
stable.transfer.AGENT = AGENT


def class_map(classes):
    multi = [tuple(group) for group in classes if len(group) > 1]
    member_to_rep = {
        tuple(member): tuple(group[0])
        for group in multi
        for member in group
    }
    return multi, member_to_rep


def install_overlay(controller, certified_states, classes, counters, *, refill):
    multi, member_to_rep = class_map(classes)
    original = controller._catalog

    def transformed_catalog(self, obs):
        catalog = original(obs)
        if obs.evidence_sha256 not in certified_states:
            return catalog

        counters["certified_catalog_calls"] += 1
        original_primary = tuple(self._primary)
        target_width = len(original_primary)
        original_primary_keys = {
            self._action_key(token) for token in original_primary
        }

        kept = []
        kept_keys = set()
        for token in catalog:
            key = self._action_key(token)
            rep = member_to_rep.get(key)
            if rep is not None and key != rep:
                counters["suppressed_candidates"] += 1
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

        counters["primary_after_compression"] += len(primary)
        counters["primary_before"] += target_width

        if refill:
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
        counters["primary_final"] += len(self._primary)
        return tuple(kept)

    controller._catalog = MethodType(transformed_catalog, controller)


def run_arm(
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
        card_id="action-quotient-reinvest",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    if certified_states:
        install_overlay(
            policy.controller,
            set(certified_states),
            classes,
            counters,
            refill=bool(refill),
        )

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    state_sequence = []
    unique_states = set()
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []
    certified_visits = 0

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        state_sequence.append(before_digest)
        unique_states.add(before_digest)
        certified_visits += int(
            bool(certified_states) and before_digest in certified_states
        )
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
        after_digest = module.normalize_frame(latest).evidence_sha256
        unique_states.add(after_digest)
        zero_change += int(before_digest == after_digest)
        actions.append(key)
        sources[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": len(actions) + 1})
        frames.append(latest)

    arc.close_scorecard()
    return {
        "actions": len(actions) + 1,
        "action_sequence": [list(key) for key in actions],
        "state_sequence": state_sequence,
        "unique_states": sorted(unique_states),
        "unique_state_count": len(unique_states),
        "distinct_actions": len(set(actions)),
        "distinct_action6": len({key for key in actions if key[0] == 6}),
        "zero_observation_change": zero_change,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "source_counts": dict(sources),
        "certified_state_visits": certified_visits,
        "catalog": dict(counters),
        "memory_digest": policy.controller.memory.digest(),
    }


def compact(row):
    return {
        key: value
        for key, value in row.items()
        if key not in ("action_sequence", "state_sequence", "unique_states")
    }


def delta_set(left, right):
    return sorted(set(map(tuple, right)) - set(map(tuple, left)))


def first_divergence(left, right):
    for index, (a, b) in enumerate(zip(left, right), start=1):
        if a != b:
            return {"action_index": index, "left": a, "right": b}
    if len(left) != len(right):
        return {
            "action_index": min(len(left), len(right)) + 1,
            "left_length": len(left),
            "right_length": len(right),
        }
    return None


def main():
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]

    stable.aq.OUT = OUT
    stable.aq.AGENT = AGENT
    module, prefixes, visits, protected, trace = stable.aq.collect_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    selected, state_rows, common, classes, class_rows = stable.derive_stable_classes(
        module,
        game_id,
        manifest["environments_dir"],
        prefixes,
        visits,
        protected,
    )
    certified_states = {digest for _count, digest in selected}

    if (6, 31, 63) in common:
        raise AssertionError("unsupported coordinate re-entered stable core")
    if [len(group) for group in classes[:2]] != [50, 5]:
        raise AssertionError("stable ft09 action classes changed")

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

    if baseline["max_levels"] != 0:
        raise AssertionError("frozen ft09 baseline changed")
    if compressed["max_levels"] < baseline["max_levels"]:
        raise AssertionError("compression arm regressed protected progress")
    if reinvested["max_levels"] < baseline["max_levels"]:
        raise AssertionError("reinvestment arm regressed protected progress")
    if reinvested["certified_state_visits"] < 1:
        raise AssertionError("reinvestment never reached certified contexts")
    if reinvested["catalog"].get("refill_slots", 0) < 1:
        raise AssertionError("certified savings were not reinvested")
    if reinvested["catalog"].get("novel_primary_candidates", 0) < 1:
        raise AssertionError("reinvestment added no new primary interventions")

    report = {
        "interpretation": (
            "certified ft09 action redundancy is reinvested into later grounded "
            "interventions inside the unchanged 400-action budget"
        ),
        "claim_boundary": (
            "quotient/refill applies only at twelve exact replay-certified public "
            "states; outside them the frozen MG-ARC5 catalog is unchanged"
        ),
        "prior_commit": "fd48a1fcb807247970bf86985c6bfcc848ac742f",
        "game_id": game_id,
        "trace": trace,
        "certified_state_count": len(certified_states),
        "common_action_count": len(common),
        "stable_class_sizes": [len(group) for group in classes],
        "baseline": compact(baseline),
        "compressed": compact(compressed),
        "reinvested": compact(reinvested),
        "novel_actions_vs_baseline": [
            list(action)
            for action in delta_set(
                baseline["action_sequence"],
                reinvested["action_sequence"],
            )
        ],
        "novel_states_vs_baseline": sorted(
            set(reinvested["unique_states"]) - set(baseline["unique_states"])
        ),
        "novel_states_vs_compressed": sorted(
            set(reinvested["unique_states"]) - set(compressed["unique_states"])
        ),
        "first_baseline_reinvest_divergence": first_divergence(
            baseline["action_sequence"],
            reinvested["action_sequence"],
        ),
        "first_compress_reinvest_divergence": first_divergence(
            compressed["action_sequence"],
            reinvested["action_sequence"],
        ),
    }
    audit.write_json(OUT / "action-quotient-reinvest.json", report)
    print(
        "ACTION_QUOTIENT_REINVEST_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_ACTION_QUOTIENT_REINVEST=PASS", flush=True)


if __name__ == "__main__":
    main()
