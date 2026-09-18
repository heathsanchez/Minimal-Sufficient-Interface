"""Try to compile post-certificate ls20 nuisance factors into a representation.

The preceding equivalence-factor diagnostic found two repeatable translations
inside replay-bisimulation-certified classes:

A) a 25-cell composite:
   - color 12, area 10, bbox 5x2, shape 2534f6a2c760c720
   - color  9, area 15, bbox 5x3, shape 497704099219a9d1
   paired at the same x with the color-9 component two rows below.

B) a 2x2 color-9 square:
   - color 9, area 4, bbox 2x2, shape 39b0bda7c3339eee

The pairwise certificates show A moving over color 3 and B moving over color 5.
This probe therefore erases only those certificate-derived absolute positions,
then audits *every raw state on the frozen ls20 trace* for new collisions.

A normalization is not promoted merely because it explains the certified
examples. Any new collision must already be separated, remain UNKNOWN, or close
under exact replay continuation obligations. Unsafe collisions falsify the
global factor immediately.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import hashlib
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "certified-factor-normalization-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import interventional_separator_probe as sep
import interventional_closure_probe as closure
import equivalence_factor_diagnostic as factors

sep.OUT = OUT
sep.AGENT = AGENT
closure.OUT = OUT
closure.AGENT = AGENT
factors.OUT = OUT
factors.AGENT = AGENT

A12 = (12, 10, (5, 2), "2534f6a2c760c720")
A9 = (9, 15, (5, 3), "497704099219a9d1")
B9 = (9, 4, (2, 2), "39b0bda7c3339eee")


def component_rows(grid):
    if not grid:
        return []
    h, w = len(grid), len(grid[0])
    seen = set()
    rows = []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen:
                continue
            value = int(grid[y][x])
            stack = [(x, y)]
            seen.add((x, y))
            cells = []
            while stack:
                px, py = stack.pop()
                cells.append((px, py))
                for nx, ny in (
                    (px - 1, py), (px + 1, py),
                    (px, py - 1), (px, py + 1),
                ):
                    if (
                        0 <= nx < w
                        and 0 <= ny < h
                        and (nx, ny) not in seen
                        and int(grid[ny][nx]) == value
                    ):
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            ox = min(px for px, _ in cells)
            oy = min(py for _, py in cells)
            shape = tuple(sorted((px - ox, py - oy) for px, py in cells))
            bw = max(px for px, _ in cells) - ox + 1
            bh = max(py for _, py in cells) - oy + 1
            rows.append({
                "signature": (
                    value,
                    len(cells),
                    (bw, bh),
                    factors.shape_digest(shape),
                ),
                "origin": (ox, oy),
                "cells": tuple(cells),
            })
    return rows


def normalize_grid(grid):
    mutable = [list(map(int, row)) for row in grid]
    components = component_rows(grid)
    by_sig = defaultdict(list)
    for row in components:
        by_sig[row["signature"]].append(row)

    a12 = by_sig.get(A12, ())
    a9 = by_sig.get(A9, ())
    masked_a = 0
    used_a9 = set()
    for left in a12:
        x, y = left["origin"]
        matches = [
            (index, right)
            for index, right in enumerate(a9)
            if index not in used_a9
            and right["origin"] == (x, y + 2)
        ]
        if not matches:
            continue
        index, right = matches[0]
        used_a9.add(index)
        for px, py in left["cells"]:
            mutable[py][px] = 3
        for px, py in right["cells"]:
            mutable[py][px] = 3
        masked_a += 1

    masked_b = 0
    for row in by_sig.get(B9, ()):
        for px, py in row["cells"]:
            mutable[py][px] = 5
        masked_b += 1

    return tuple(tuple(row) for row in mutable), {
        "factor_a_composites": masked_a,
        "factor_b_squares": masked_b,
    }


def canonical_digest(grid, protected, legal):
    normalized, stats = normalize_grid(grid)
    payload = repr((tuple(protected), tuple(legal), normalized)).encode()
    return hashlib.sha256(payload).hexdigest(), stats


def build_trace_with_grids(game_id, envdir, max_actions):
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
        raise RuntimeError("offline ls20 unavailable")

    policy = module.MyAgent(
        card_id="factor-normalization-source",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    q = sep.PartialInterventionalQuotient()
    latest = policy._convert_raw_frame_data(env.observation_space)
    digest = sep.raw_digest(module, latest)
    q.observe_node(
        digest,
        protected=sep.protected(latest),
        legal_actions=sep.legal_ids(latest),
    )
    grids = {digest: module.settled_grid(latest)}
    prefixes = {digest: ()}
    prefix = ()
    frames = [latest]
    actions = []
    sources = Counter()

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break
        before = latest
        source = digest
        before_level = int(before.levels_completed)
        action = policy.choose_action(frames, before)
        data = audit.validate_action(action, before)
        key = (int(action.value), data.get("x"), data.get("y"))
        reasoning = getattr(action, "reasoning", {})
        source_name = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )
        raw = env.step(action, data=data, reasoning={"source": source_name})
        latest = policy._convert_raw_frame_data(raw)
        digest = sep.raw_digest(module, latest)
        q.observe_node(
            digest,
            protected=sep.protected(latest),
            legal_actions=sep.legal_ids(latest),
        )
        delta = int(latest.levels_completed) - before_level
        outcome = (
            "LEVEL_INCREMENT" if delta > 0 else audit.state_name(latest),
            int(delta),
        )
        q.observe_transition(source, int(action.value), digest, outcome=outcome)
        actions.append(key)
        sources[source_name] += 1
        prefix = prefix + (key,)
        prefixes.setdefault(digest, prefix)
        grids.setdefault(digest, module.settled_grid(latest))
        frames.append(latest)

    arc.close_scorecard()
    return module, q, prefixes, grids, {
        "actions": len(actions) + 1,
        "raw_states": len(q.nodes),
        "source_counts": dict(sources),
    }


def known_certified_pairs():
    out = set()
    for group in factors.CLASSES:
        for left, right in combinations(sorted(group), 2):
            out.add(tuple(sorted((left, right))))
    return out


def main():
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ls20-")
    )
    game_id = game["game_id"]

    module, q, prefixes, grids, source_meta = build_trace_with_grids(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    source_nodes = set(q.nodes)
    if len(source_nodes) != 355:
        raise AssertionError("frozen ls20 source trace changed")

    # Reproduce the active evidence that licensed the factor hypothesis first.
    initial_classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    candidates = sep.merged_pairs(initial_classes, source_nodes)
    if len(candidates) != 15:
        raise AssertionError("ls20 observer residual changed")
    closure_results = factors.reproduce_certificate_context(
        module,
        q,
        prefixes,
        game_id,
        manifest["environments_dir"],
        candidates,
    )

    known = known_certified_pairs()
    canonical = defaultdict(list)
    node_factor_stats = {}
    for node in sorted(source_nodes):
        digest, stats = canonical_digest(
            grids[node],
            q.nodes[node].protected,
            q.nodes[node].legal_actions,
        )
        canonical[digest].append(node)
        node_factor_stats[node] = stats

    collision_groups = [
        sorted(group)
        for group in canonical.values()
        if len(group) > 1
    ]
    collision_pairs = sorted({
        tuple(sorted((left, right)))
        for group in collision_groups
        for left, right in combinations(group, 2)
    })

    # First use already-available transition evidence to reject over-broad
    # canonicalization without spending any new interventions.
    classes_after_cert = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    already_refuted = []
    already_same = []
    for pair in collision_pairs:
        if pair in known:
            continue
        if classes_after_cert[pair[0]] != classes_after_cert[pair[1]]:
            already_refuted.append(pair)
        else:
            already_same.append(pair)

    closer = closure.ClosureProbe(
        module,
        q,
        prefixes,
        game_id,
        manifest["environments_dir"],
    )
    active_results = [closer.close_root(pair) for pair in already_same]

    newly_closed = [
        row for row in active_results
        if row["status"] == "CLOSED_BOUNDED_REPLAY_BISIMULATION"
    ]
    newly_separated = [
        row for row in active_results
        if row["status"] == "SEPARATED"
    ]
    unknown = [
        row for row in active_results
        if row["status"].startswith("UNKNOWN")
    ]

    known_covered = [
        pair for pair in collision_pairs
        if pair in known
    ]
    unsafe_pairs = len(already_refuted) + len(newly_separated)
    global_promotion = unsafe_pairs == 0 and not unknown

    report = {
        "interpretation": (
            "post-certificate attempt to erase two translation nuisance factors "
            "from the ls20 representation, audited against all 355 source states"
        ),
        "claim_boundary": (
            "global factor promotion requires every induced collision to be "
            "already certified or closed by exact replay; any separator falsifies it"
        ),
        "prior_commit": "86ab9c26ccbe31acebc78deda300c247df03d635",
        "game_id": game_id,
        "source_trace": source_meta,
        "certificate_roots_reproduced": len(closure_results),
        "source_states": len(source_nodes),
        "states_with_factor_a": sum(
            row["factor_a_composites"] > 0
            for row in node_factor_stats.values()
        ),
        "states_with_factor_b": sum(
            row["factor_b_squares"] > 0
            for row in node_factor_stats.values()
        ),
        "canonical_state_count": len(canonical),
        "canonical_collision_groups": len(collision_groups),
        "canonical_collision_pairs": len(collision_pairs),
        "known_certified_collision_pairs": len(known_covered),
        "already_refuted_new_pairs": len(already_refuted),
        "already_refuted_examples": already_refuted[:24],
        "active_new_pairs": len(already_same),
        "active_new_probes": closer.new_probes,
        "newly_closed_pairs": len(newly_closed),
        "newly_separated_pairs": len(newly_separated),
        "unknown_pairs": len(unknown),
        "active_results": active_results,
        "global_factor_promotion": global_promotion,
    }
    audit.write_json(OUT / "certified-factor-normalization.json", report)
    print(
        "CERTIFIED_FACTOR_NORMALIZATION_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_CERTIFIED_FACTOR_NORMALIZATION=PASS", flush=True)


if __name__ == "__main__":
    main()
