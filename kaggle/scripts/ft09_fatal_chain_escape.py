"""Search one-deviation escapes from ft09's exact fatal (54,54) chains.

The retained bank established that repeated Action 6 at (54,54) is highly
controllable but the three previously-unobserved endpoints all continue to
GAME_OVER. This experiment asks the smallest useful counterfactual:

    At the last few exact states before GAME_OVER, does one different primary
    intervention break the fatal chain?

For each of the final nonterminal states on each verified fatal chain:
- exact-replay the full RESET prefix and recover the source digest;
- reconstruct the frozen controller's primary catalog at that exact frame;
- rank alternative primary actions by retained exact state-change rate
  (proposal-only);
- apply one alternative;
- resume (54,54) for a bounded continuation;
- stop on protected progress, GAME_OVER, no-change, or a repeated digest.

Every replay source is exact. No alternative is promoted from the prior alone.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ft09-fatal-chain-escape-results"
AGENT = OUT / "agent.py"
BANK = OUT / "dynamic-exact-effect-bank.json"
PROGRESSION = OUT / "ft09-5454-progression.json"

sys.path.insert(0, str(ROOT / "kaggle" / "src"))
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

from metalogic_arc3.consequence_controller import settled_grid
import action_quotient_diagnostic as aq

aq.OUT = OUT
aq.AGENT = AGENT

TARGET_ACTION = (6, 54, 54)
TAIL_STATES_PER_CHAIN = 6
TAIL_OFFSET = 24
ALTERNATIVES_PER_STATE = 6
MAX_RESUME = 40

EXPECTED_AGENT_SHA = "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead"
EXPECTED_BANK_EDGES = 945
EXPECTED_BANK_CATALOGS = 425


def load_inputs():
    bank = json.loads(BANK.read_text())
    if bank.get("schema") != "arc3-exact-effect-bank-v1":
        raise AssertionError("unexpected effect-bank schema")
    if bank.get("agent_sha256") != EXPECTED_AGENT_SHA:
        raise AssertionError("effect-bank agent mismatch")
    if len(bank.get("edges", ())) != EXPECTED_BANK_EDGES:
        raise AssertionError("effect-bank edge count changed")
    if len(bank.get("catalogs", {})) != EXPECTED_BANK_CATALOGS:
        raise AssertionError("effect-bank catalog count changed")

    progression = json.loads(PROGRESSION.read_text())
    if progression["result"]["status"] != "NO_PROTECTED_PROGRESS":
        raise AssertionError("fatal-chain premise changed")
    if len(progression["endpoint_results"]) != 3:
        raise AssertionError("expected three fatal endpoint chains")
    return bank, progression


def change_prior(bank):
    rows = defaultdict(lambda: [0, 0, set()])
    for item in bank["edges"]:
        action = tuple(item["action"])
        row = item["row"]
        n = int(row.get("n", 0))
        changed = int(row.get("changed", 0))
        rows[action][0] += n
        rows[action][1] += changed
        rows[action][2].add(str(item["context"]))
    return {
        action: {
            "observations": n,
            "changed": changed,
            "contexts": len(contexts),
            "rate": ((changed + 1.0) / (n + 2.0)),
        }
        for action, (n, changed, contexts) in rows.items()
    }


def make_action(action_key):
    from arcengine import GameAction

    action_id, x, y = tuple(action_key)
    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        if x is None or y is None:
            raise AssertionError("complex action missing coordinates")
        action.set_data({"x": int(x), "y": int(y)})
    return action, action.action_data.model_dump()


def source_specs(progression):
    specs = []
    for chain_index, chain in enumerate(progression["endpoint_results"], start=1):
        route = tuple(tuple(action) for action in chain["route"])
        extension = list(chain["extension"])
        if not extension or extension[-1]["state"] != "GAME_OVER":
            raise AssertionError("expected exact fatal chain ending in GAME_OVER")

        nonterminal = extension[:-1]
        end = max(0, len(nonterminal) - TAIL_OFFSET)
        start = max(0, end - TAIL_STATES_PER_CHAIN)
        for row in nonterminal[start:end]:
            step = int(row["step"])
            source = str(row["source"])
            prefix = route + (TARGET_ACTION,) * (step - 1)
            specs.append({
                "chain": chain_index,
                "source": source,
                "fatal_step": step,
                "prefix": prefix,
                "distance_to_game_over": len(extension) - step + 1,
            })
    specs.sort(key=lambda row: (row["distance_to_game_over"], row["chain"], row["source"]))
    return specs


def replay_to_source(module, game_id, envdir, prefix, expected_source):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ft09 unavailable")

    adapter = module.MyAgent(
        card_id="fatal-chain-escape",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    adapter.controller.archived_capabilities = ()

    latest = adapter._convert_raw_frame_data(env.observation_space)
    for action_key in prefix:
        action, data = make_action(action_key)
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "fatal_chain_replay"},
        )
        latest = adapter._convert_raw_frame_data(raw)

    digest = str(module.normalize_frame(latest).evidence_sha256)
    if digest != expected_source:
        arc.close_scorecard()
        raise AssertionError(
            f"fatal-chain replay mismatch: {expected_source[:12]} != {digest[:12]}"
        )
    return arc, env, adapter, latest


def primary_alternatives(module, adapter, latest, priors):
    obs = module.normalize_frame(latest)
    controller = adapter.controller
    controller._grid = settled_grid(latest)
    controller._raster_cache = None
    catalog = controller._catalog(obs)
    primary = tuple(controller._primary) or tuple(catalog)

    rows = []
    seen = set()
    for token in primary:
        key = controller._action_key(token)
        if key == TARGET_ACTION or key in seen:
            continue
        seen.add(key)
        prior = priors.get(
            key,
            {"rate": 0.5, "contexts": 0, "observations": 0, "changed": 0},
        )
        rows.append((
            -float(prior["rate"]),
            -int(prior["contexts"]),
            -int(prior["observations"]),
            controller._candidate_key(token),
            tuple(key),
            prior,
        ))
    rows.sort()
    return [
        {"action": row[4], "prior": row[5]}
        for row in rows[:ALTERNATIVES_PER_STATE]
    ]


def test_escape(
    module,
    game_id,
    envdir,
    source_spec,
    alternative,
):
    arc, env, adapter, latest = replay_to_source(
        module,
        game_id,
        envdir,
        source_spec["prefix"],
        source_spec["source"],
    )

    start = module.normalize_frame(latest)
    start_level = int(start.levels_completed)
    action_key = tuple(alternative["action"])

    action, data = make_action(action_key)
    raw = env.step(
        action,
        data=data,
        reasoning={"source": "fatal_chain_escape"},
    )
    latest = adapter._convert_raw_frame_data(raw)
    after = module.normalize_frame(latest)
    after_digest = str(after.evidence_sha256)

    word = tuple(source_spec["prefix"]) + (action_key,)
    rows = [{
        "phase": "escape",
        "action": list(action_key),
        "source": source_spec["source"],
        "target": after_digest,
        "changed": after_digest != source_spec["source"],
        "state": str(after.state),
        "level": int(after.levels_completed),
    }]

    if int(after.levels_completed) > start_level:
        arc.close_scorecard()
        return {
            "status": "PROTECTED_PROGRESS",
            "rows": rows,
            "progress": {
                "level": int(after.levels_completed),
                "executed_actions": len(word),
                "reported_milestone_action": len(word) + 1,
                "action_word": [list(action) for action in word],
                "target": after_digest,
            },
        }

    if str(after.state) in ("GAME_OVER", "WIN"):
        arc.close_scorecard()
        return {"status": str(after.state), "rows": rows, "progress": None}

    if after_digest == source_spec["source"]:
        arc.close_scorecard()
        return {"status": "ESCAPE_NO_CHANGE", "rows": rows, "progress": None}

    seen = {source_spec["source"], after_digest}
    for step in range(1, MAX_RESUME + 1):
        current = module.normalize_frame(latest)
        if 6 not in {int(value) for value in current.available_actions}:
            arc.close_scorecard()
            return {"status": "ACTION6_NOT_LEGAL", "rows": rows, "progress": None}

        before_digest = str(current.evidence_sha256)
        before_level = int(current.levels_completed)
        action, data = make_action(TARGET_ACTION)
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "fatal_chain_resume_5454"},
        )
        latest = adapter._convert_raw_frame_data(raw)
        nxt = module.normalize_frame(latest)
        nxt_digest = str(nxt.evidence_sha256)
        word = word + (TARGET_ACTION,)

        rows.append({
            "phase": "resume",
            "step": step,
            "action": list(TARGET_ACTION),
            "source": before_digest,
            "target": nxt_digest,
            "changed": nxt_digest != before_digest,
            "state": str(nxt.state),
            "level": int(nxt.levels_completed),
        })

        if int(nxt.levels_completed) > start_level:
            arc.close_scorecard()
            return {
                "status": "PROTECTED_PROGRESS",
                "rows": rows,
                "progress": {
                    "level": int(nxt.levels_completed),
                    "executed_actions": len(word),
                    "reported_milestone_action": len(word) + 1,
                    "action_word": [list(action) for action in word],
                    "target": nxt_digest,
                },
            }
        if str(nxt.state) in ("GAME_OVER", "WIN"):
            arc.close_scorecard()
            return {"status": str(nxt.state), "rows": rows, "progress": None}
        if nxt_digest == before_digest:
            arc.close_scorecard()
            return {"status": "RESUME_NO_CHANGE", "rows": rows, "progress": None}
        if nxt_digest in seen:
            arc.close_scorecard()
            return {"status": "REPEATED_DIGEST", "rows": rows, "progress": None}
        seen.add(nxt_digest)

    arc.close_scorecard()
    return {"status": "RESUME_BOUND", "rows": rows, "progress": None}


def main():
    bank, progression = load_inputs()
    priors = change_prior(bank)

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]

    audit.AGENT = AGENT
    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    specs = source_specs(progression)
    results = []
    progress = None

    for source_spec in specs:
        arc, _env, adapter, latest = replay_to_source(
            module,
            game_id,
            manifest["environments_dir"],
            source_spec["prefix"],
            source_spec["source"],
        )
        alternatives = primary_alternatives(module, adapter, latest, priors)
        arc.close_scorecard()

        for alt in alternatives:
            result = test_escape(
                module,
                game_id,
                manifest["environments_dir"],
                source_spec,
                alt,
            )
            row = {
                "chain": source_spec["chain"],
                "source": source_spec["source"],
                "fatal_step": source_spec["fatal_step"],
                "distance_to_game_over": source_spec["distance_to_game_over"],
                "prefix_actions": len(source_spec["prefix"]),
                "alternative": list(alt["action"]),
                "prior": alt["prior"],
                "status": result["status"],
                "progress": result["progress"],
                "rows": result["rows"],
            }
            results.append(row)

            print(
                "FT09_FATAL_ESCAPE_PROBE="
                + json.dumps(
                    {k: v for k, v in row.items() if k != "rows"},
                    sort_keys=True,
                ),
                flush=True,
            )

            if result["progress"] is not None:
                progress = result["progress"]
                break
        if progress is not None:
            break

    report = {
        "interpretation": (
            "one-deviation counterfactual search on the final upstream band of exact "
            "states before the retained ft09 (54,54) fatal GAME_OVER chains"
        ),
        "claim_boundary": (
            "alternative ranking uses historical exact change support as proposal-only; "
            "every source is recovered by exact replay and every tested consequence "
            "is observed live"
        ),
        "source_chain_count": 3,
        "tail_offset": TAIL_OFFSET,
        "source_state_count": len(specs),
        "alternatives_per_state": ALTERNATIVES_PER_STATE,
        "resume_bound": MAX_RESUME,
        "probe_count": len(results),
        "result": {
            "status": "PROGRESS_FOUND" if progress is not None else "NO_PROTECTED_PROGRESS",
            "progress": progress,
        },
        "probes": results,
    }

    audit.write_json(
        OUT / "ft09-fatal-chain-escape.json",
        report,
    )
    print(
        "FT09_FATAL_CHAIN_ESCAPE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_FT09_FATAL_CHAIN_ESCAPE=PASS", flush=True)


if __name__ == "__main__":
    main()
