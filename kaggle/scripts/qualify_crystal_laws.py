from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.crystal_laws import (
    ArcCrystalLawBridge,
    ArcLawBinding,
    Prediction,
    VerifiedLawStore,
)

OUT = ROOT / "evidence" / "arc3-crystal-law-query-v1" / "result.json"


def main() -> None:
    store = VerifiedLawStore.default()
    bridge = ArcCrystalLawBridge(store)
    action = (3, None, None)
    bindings = (
        ArcLawBinding(("situation-1",), action, 2, ("a0", "a1", "a0"), ("s1",)),
        ArcLawBinding(("situation-2",), action, 3, ("b0", "b1", "b2", "b0"), ("s2",)),
    )
    for binding in bindings:
        bridge.admit_binding(binding)
    cycle_answers = [
        bridge.normalize_repetition(
            binding.context, binding.action, 8, live_supports=binding.support_refs
        )
        for binding in bindings
    ]

    a = (1, None, None)
    b = (2, None, None)
    hypotheses = ("h1", "h2", "h3")
    table = {(h, a): "same" for h in hypotheses}
    table.update({("h1", b): "x", ("h2", b): "y", ("h3", b): "z"})
    predictions = tuple(
        Prediction(h, act, table[(h, act)])
        for h in hypotheses for act in (a, b)
    )
    separator = bridge.choose_separator(
        hypotheses=hypotheses,
        actions=(a, b),
        predictions=predictions,
        support_refs=("model:frozen",),
        live_supports=("model:frozen",),
    )
    incomplete = bridge.choose_separator(
        hypotheses=("h1", "h2"),
        actions=(a,),
        predictions=(Prediction("h1", a, "x"),),
        support_refs=("model:x",),
        live_supports=("model:x",),
    )
    unbound = ArcCrystalLawBridge(store).normalize_repetition(
        ("unseen",), action, 8
    )
    revoked = bridge.normalize_repetition(
        bindings[0].context, action, 8, live_supports=()
    )

    out = {
        "schema": "msi.arc3-crystal-law-query-v1.qualified",
        "status": "QUALIFIED_BOUNDED",
        "law_ids": list(store.law_ids),
        "cycle_transfer": {
            "distinct_contexts": 2,
            "baseline_actions": 16,
            "crystal_actions": sum(x.reduced_count for x in cycle_answers),
            "actions_saved": 16 - sum(x.reduced_count for x in cycle_answers),
            "same_law_id": len({x.law_id for x in cycle_answers}) == 1,
        },
        "separator_transfer": {
            "hypotheses": list(hypotheses),
            "chosen_action": list(separator.chosen_action or ()),
            "worst_case_survivors": separator.worst_case_survivors,
            "frozen_baseline_probes": 2,
            "crystal_probes": 1,
        },
        "fail_closed": {
            "missing_cycle_binding": unbound.status.value,
            "revoked_cycle_support": revoked.status.value,
            "incomplete_prediction_table": incomplete.status.value,
        },
        "authority_boundary": (
            "The laws are reusable mathematical procedures. ARC applicability is "
            "separate evidence: cycle bindings and prediction tables must be locally "
            "supported. This gate does not claim a public/private ARC-3 score gain."
        ),
        "next_residual": (
            "Populate separator predictions from an online learned ARC world-model "
            "and compare matched action efficiency on held-out situations."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
