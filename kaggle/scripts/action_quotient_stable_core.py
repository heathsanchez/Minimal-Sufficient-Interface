"""Extract and operationally test the stable core of the ft09 action quotient.

The previous transfer probe learned a 51-member class from two states.  On all
eight held states exactly one member, (6,31,63), was absent; the other 50
members stayed consequence-identical.  This experiment removes that unsupported
member by construction, recomputes the maximal consequence-equivalence classes
over *all* recurrent exact states selected from the frozen trajectory, and then
compiles only those cross-state-certified classes into the candidate catalog at
the exact states on which they were certified.

Outside those exact public states the policy is unchanged.  Raw consequence
recording and protected outcomes remain unchanged everywhere.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "action-quotient-stable-core-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import action_quotient_diagnostic as aq
import action_quotient_transfer as transfer

aq.OUT = OUT
aq.AGENT = AGENT
transfer.OUT = OUT
transfer.AGENT = AGENT

RECURRENT_STATES = 12


def derive_stable_classes(module, game_id, envdir, prefixes, visits, protected):
    eligible = [
        (count, digest)
        for digest, count in visits.items()
        if protected[digest][0] == "NOT_FINISHED" and count > 1
    ]
    eligible.sort(key=lambda row: (-row[0], len(prefixes[row[1]]), row[1]))
    selected = eligible[:RECURRENT_STATES]
    if len(selected) != RECURRENT_STATES:
        raise AssertionError("expected twelve recurrent exact ft09 states")

    tables = []
    state_rows = []
    for count, digest in selected:
        table, _descriptors = transfer.consequence_table(
            module, game_id, envdir, digest, prefixes[digest]
        )
        tables.append(table)
        state_rows.append({
            "source": digest,
            "visits": int(count),
            "prefix_length": len(prefixes[digest]),
            "candidate_actions": len(table),
            "consequence_classes": len(set(table.values())),
        })
        print(
            "STABLE_CORE_STATE="
            + json.dumps(state_rows[-1], sort_keys=True),
            flush=True,
        )

    common = set.intersection(*(set(table) for table in tables))
    signatures = defaultdict(list)
    for action in sorted(common):
        signatures[tuple(table[action] for table in tables)].append(action)

    classes = sorted(
        (tuple(sorted(group)) for group in signatures.values()),
        key=lambda group: (-len(group), group),
    )
    rows = [
        {
            "class_id": index,
            "size": len(group),
            "representative": list(group[0]),
            "members": [list(action) for action in group],
        }
        for index, group in enumerate(classes)
    ]
    return selected, state_rows, common, classes, rows


def install_catalog_quotient(controller, certified_states, classes, counters):
    multi = [group for group in classes if len(group) > 1]
    member_to_rep = {
        member: group[0]
        for group in multi
        for member in group
    }
    original = controller._catalog

    def quotient_catalog(self, obs):
        catalog = original(obs)
        if obs.evidence_sha256 not in certified_states:
            return catalog

        counters["certified_state_catalog_calls"] += 1
        before = len(catalog)
        kept = []
        seen = set()
        for token in catalog:
            key = self._action_key(token)
            rep = member_to_rep.get(key)
            if rep is not None and key != rep:
                counters["suppressed_candidates"] += 1
                continue
            if key in seen:
                continue
            seen.add(key)
            kept.append(token)

        allowed = {self._action_key(token) for token in kept}
        self._primary = tuple(
            token for token in self._primary
            if self._action_key(token) in allowed
        )
        counters["catalog_entries_before"] += before
        counters["catalog_entries_after"] += len(kept)
        return tuple(kept)

    controller._catalog = MethodType(quotient_catalog, controller)


def run_policy(module, game_id, envdir, max_actions, certified_states=None, classes=()):
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
        card_id="stable-action-quotient",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    if certified_states:
        install_catalog_quotient(
            policy.controller,
            set(certified_states),
            classes,
            counters,
        )

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    sources = Counter()
    visits = Counter()
    zero_change = 0
    milestones = []
    max_level = int(latest.levels_completed)

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break
        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        visits[before_digest] += 1
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
        "distinct_actions": len(set(actions)),
        "distinct_action6": len({key for key in actions if key[0] == 6}),
        "zero_observation_change": zero_change,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "source_counts": dict(sources),
        "certified_state_visits": sum(
            count for digest, count in visits.items()
            if certified_states and digest in certified_states
        ),
        "catalog_quotient": dict(counters),
        "memory_digest": policy.controller.memory.digest(),
    }


def compact(row):
    return {key: value for key, value in row.items() if key != "action_sequence"}


def first_divergence(a, b):
    for index, (left, right) in enumerate(zip(a, b), start=1):
        if left != right:
            return {
                "action_index": index,
                "baseline": left,
                "quotient": right,
            }
    if len(a) != len(b):
        return {
            "action_index": min(len(a), len(b)) + 1,
            "baseline_length": len(a),
            "quotient_length": len(b),
        }
    return None


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

    selected, state_rows, common, classes, class_rows = derive_stable_classes(
        module,
        game_id,
        manifest["environments_dir"],
        prefixes,
        visits,
        protected,
    )
    certified_states = [digest for _count, digest in selected]
    multi = [group for group in classes if len(group) > 1]

    # Pin the residual from the previous transfer test, but promote only what
    # survives the full recurrent-state intersection.
    missing_31_63 = (6, 31, 63) not in common
    if not missing_31_63:
        raise AssertionError("known unsupported coordinate unexpectedly entered stable core")
    if not multi:
        raise AssertionError("no nontrivial stable action class survived")

    largest = multi[0]
    for table_state, (_count, digest) in zip(state_rows, selected):
        # The derivation itself guarantees equality of the vector signature.
        table_state["stable_largest_class_size"] = len(largest)

    baseline = run_policy(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    quotient = run_policy(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
    )

    if baseline["max_levels"] != 0:
        raise AssertionError("frozen ft09 baseline changed")
    if quotient["max_levels"] < baseline["max_levels"]:
        raise AssertionError("certified action quotient regressed protected progress")
    if quotient["certified_state_visits"] < 1:
        raise AssertionError("operational action quotient never activated")
    if quotient["catalog_quotient"].get("suppressed_candidates", 0) < 1:
        raise AssertionError("operational action quotient suppressed no certified redundancy")

    report = {
        "interpretation": (
            "maximal exact-action equivalence over twelve recurrent frozen-ft09 "
            "states, followed by exact-state-scoped operational catalog compression"
        ),
        "claim_boundary": (
            "classes are certified only on the twelve replayed public states; "
            "outside them the original policy/catalog is untouched"
        ),
        "prior_commit": "4253fa4b164d3a9f2a9d2711fc0551ccef985c6e",
        "game_id": game_id,
        "trace": trace,
        "recurrent_state_count": len(selected),
        "states": state_rows,
        "common_action_count": len(common),
        "stable_class_count": len(classes),
        "nontrivial_class_count": len(multi),
        "largest_stable_class": len(largest),
        "stable_action_compression": len(common) / max(1, len(classes)),
        "known_removed_unsupported_action": [6, 31, 63],
        "classes": class_rows,
        "baseline": compact(baseline),
        "quotient": compact(quotient),
        "first_action_divergence": first_divergence(
            baseline["action_sequence"], quotient["action_sequence"]
        ),
    }
    audit.write_json(OUT / "action-quotient-stable-core.json", report)
    print(
        "ACTION_QUOTIENT_STABLE_CORE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_ACTION_QUOTIENT_STABLE_CORE=PASS", flush=True)


if __name__ == "__main__":
    main()
