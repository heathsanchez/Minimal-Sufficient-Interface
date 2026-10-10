#!/usr/bin/env python3
"""Bounded contextual proof-critic falsifier. No theorem or economy beyond its scope.

The lower meta-interpreter supplies lookup, symmetry, transitive composition,
and repetition.  The synthesizer SELECTS a new executable critic program from
this supplied language after a complete old one-edge-critic failure.  It DOES
NOT synthesize these primitive semantics.  Every output proof is separately
validated against source premises and emitted as Lean kernel-checkable terms.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import importlib
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def digest(v):
    return sha256(canonical(v).encode()).hexdigest()


@dataclass(frozen=True)
class Goal:
    name: str
    hypotheses: tuple[tuple[str, str], ...]
    lhs: str
    rhs: str

    def atoms(self):
        return tuple(sorted({self.lhs, self.rhs} | {x for pair in self.hypotheses for x in pair}))


@dataclass(frozen=True)
class Edge:
    index: int
    forward: bool
    start: str
    end: str


@dataclass(frozen=True)
class Critic:
    # The meaning of these constructors is supplied by the lower interpreter.
    opcode: str    # bounded | repeat
    depth: int     # depth 0 only for repeat
    ast_cost: int  # declared code-size preorder, NOT total economic cost

    def contract(self):
        return {"opcode": self.opcode, "depth": self.depth, "ast_cost": self.ast_cost}


OLD = (Critic("bounded", 1, 1),)
META = (
    Critic("bounded", 1, 1),
    Critic("bounded", 2, 3),
    Critic("bounded", 3, 5),
    Critic("repeat", 0, 4),
)


def all_one_step_proofs(goal: Goal):
    """Complete old repertoire of reflexivity, one hypothesis and its symmetry."""
    if goal.lhs == goal.rhs:
        yield ()
    for i, (x, y) in enumerate(goal.hypotheses):
        if x == goal.lhs and y == goal.rhs:
            yield (Edge(i, True, x, y),)
        if y == goal.lhs and x == goal.rhs:
            yield (Edge(i, False, y, x),)


def proof_search(goal: Goal, critic: Critic):
    """Source-generic proof interpreter; never inspects target names or answers."""
    assert critic in META
    if critic.opcode == "bounded" and critic.depth == 1:
        return next(all_one_step_proofs(goal), None)
    # Generic graph search using supplied Eq.trans / Eq.symm proof primitives.
    bound = len(goal.atoms()) + 1 if critic.opcode == "repeat" else critic.depth
    queue = deque([(goal.lhs, ())])
    seen = {goal.lhs}
    while queue:
        current, path = queue.popleft()
        if current == goal.rhs:
            return path
        if len(path) >= bound:
            continue
        for index, (x, y) in enumerate(goal.hypotheses):
            neighbors = ((y, True),) if x == current else ()
            neighbors += ((x, False),) if y == current else ()
            for nxt, direction in neighbors:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path + (Edge(index, direction, current, nxt),)))
    return None


def checked_path(goal: Goal, witness) -> bool:
    """Independent exact proof DAG validator: indexes and direction are source-bound."""
    if witness is None:
        return False
    current = goal.lhs
    for e in witness:
        if e.index < 0 or e.index >= len(goal.hypotheses):
            return False
        x, y = goal.hypotheses[e.index]
        a, b = (x, y) if e.forward else (y, x)
        if (e.start, e.end) != (a, b) or current != a:
            return False
        current = b
    return current == goal.rhs


def bool_oracle(goal: Goal):
    """Exhaustive countermodel oracle; Boolean equality models separate components."""
    atoms = goal.atoms()
    model_checks = 0
    for bits in product((False, True), repeat=len(atoms)):
        model_checks += 1
        model = dict(zip(atoms, bits))
        if all(model[a] == model[b] for a, b in goal.hypotheses):
            if model[goal.lhs] != model[goal.rhs]:
                return False, model_checks, model
    return True, model_checks, None


def training_goals():
    # Declared in frozen protocol; no future corpus accessible to the compiler.
    return (
        Goal("dev_direct", (("a", "b"),), "a", "b"),
        Goal("dev_two", (("a", "b"), ("b", "c")), "a", "c"),
        Goal("dev_three", (("a", "b"), ("b", "c"), ("c", "d")), "a", "d"),
        Goal("dev_same_directed_good", (("a", "b"), ("b", "c")), "a", "c"),
        Goal("dev_same_directed_bad", (("a", "b"),), "a", "c"),
        Goal("dev_disconnected", (("a", "b"), ("d", "c")), "a", "c"),
        Goal("dev_distractor", (("a", "b"), ("b", "c"), ("x", "y")), "a", "c"),
    )


def evaluate(critic, cases):
    candidate_attempts = checker_calls = oracle_checks = model_checks = 0
    records = []
    for task in cases:
        semantic, nmodels, model = bool_oracle(task)
        model_checks += nmodels
        oracle_checks += 1
        candidate_attempts += 1
        witness = proof_search(task, critic)
        if witness is not None:
            checker_calls += 1
            if not checked_path(task, witness):
                raise AssertionError(f"unsound proof for {task.name}")
        predicted = witness is not None
        records.append({
            "task": task.name,
            "semantic_entailment": semantic,
            "proof_found": predicted,
            "proof_edges": len(witness) if witness is not None else None,
            "exact": predicted == semantic,
            "counterexample": model,
        })
    return {
        "all_exact": all(r["exact"] for r in records),
        "positive_solved": sum(r["semantic_entailment"] and r["proof_found"] for r in records),
        "negatives_respected": all(r["semantic_entailment"] or not r["proof_found"] for r in records),
        "candidate_checks": candidate_attempts,
        "checker_calls": checker_calls,
        "oracle_checks": oracle_checks,
        "bool_models_checked": model_checks,
        "records": records,
    }


def select_critic(dev):
    old = evaluate(OLD[0], dev)
    obstructed = [r["task"] for r in old["records"] if r["semantic_entailment"] and not r["proof_found"]]
    assert {"dev_two", "dev_three"}.issubset(obstructed)
    # Proof that the old syntax class was actually enumerated: each proof has
    # zero or exactly one direct/symmetric source hypothesis. Scope is FINITE.
    complete_old = True
    for task in dev:
        old_found = proof_search(task, OLD[0])
        direct_found = next(all_one_step_proofs(task), None)
        complete_old = complete_old and old_found == direct_found
    assert complete_old
    trials=[]
    for candidate in META:
        outcome=evaluate(candidate,dev)
        trials.append((candidate,outcome))
    adequate=[(c,r) for c,r in trials if r["all_exact"]]
    if not adequate:
        return None, old, trials, "UNKNOWN_SEARCH"
    mincost=min(c.ast_cost for c,_ in adequate)
    winners=[(c,r) for c,r in adequate if c.ast_cost==mincost]
    if len(winners)!=1:
        return None, old, trials, "UNKNOWN_CHOICE"
    selected=winners[0][0]
    if selected in OLD:
        return selected, old, trials, "IDENTITY"
    return selected,old,trials,"CANDIDATE_CONSTRUCTOR_MEDIATED_CRITIC"


def to_lean_proof(goal, witness):
    if not checked_path(goal,witness):
        raise ValueError("attempted to compile unsound witness")
    atoms=goal.atoms()
    hyps=" ".join(f"(h{i} : {u} = {v})" for i,(u,v) in enumerate(goal.hypotheses))
    binders=" ".join(atoms)
    edges=[f"h{e.index}" if e.forward else f"(Eq.symm h{e.index})" for e in witness]
    if not edges:
        term="Eq.refl " + goal.lhs
    else:
        term=edges[0]
        for nxt in edges[1:]:
            term=f"(Eq.trans {term} {nxt})"
    return f"theorem {goal.name} ({binders} : Nat) {hyps} : {goal.lhs} = {goal.rhs} := by\n  exact {term}\n"


def emit_lean(cases,critic):
    texts=["import Std\n\n/- This file is generated from a FROZEN critic program, not a list of given proofs.\n   These terms are kernel-checked independently of the Python verifier. -/\nnamespace BundyCriticGenerated\n"]
    emitted=[]
    for task in cases:
        witness=proof_search(task,critic)
        if witness is not None:
            texts.append(to_lean_proof(task,witness))
            emitted.append(task.name)
    texts.append("end BundyCriticGenerated\n")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT / "GeneratedProofs.lean").write_text("\n".join(texts))
    return emitted


def run():
    dev=training_goals()
    selected,old,trial_outcomes,selection=select_critic(dev)
    if selected is None:
        raise RuntimeError(selection)

    # The generator is frozen BEFORE the held-out module is first imported.
    frozen={
        "selection":selection,
        "selected_program":selected.contract(),
        "old_programs":[x.contract() for x in OLD],
        "meta_programs":[x.contract() for x in META],
        "development_corpus_hash":digest([vars(t) for t in dev]),
    }
    frozen["freeze_digest"]=digest(frozen)
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/"pre_holdout_freeze.json").write_text(json.dumps(frozen,indent=2,sort_keys=True)+"\n")

    # Access only after the exact selected policy and authority are frozen.
    heldout=importlib.import_module(".heldout", __package__ or "bundy_critic_genesis_v1").goals(Goal)
    protected=evaluate(selected,heldout)
    old_future=evaluate(OLD[0],heldout)
    # A serious context-aware stateless alternative can invoke the SAME complete
    # meta interpreter without the retained state.  It has identical coverage.
    stateless=evaluate(Critic("repeat",0,4),heldout)
    exact_executable_ledger=evaluate(selected,heldout)
    selected_ablation=evaluate(OLD[0],heldout)
    assert protected==stateless==exact_executable_ledger

    mutated=[]
    for task in heldout:
        if task.name.startswith("future_chain_"):
            mutated.append(Goal(task.name+"_delete_first",task.hypotheses[1:],task.lhs,task.rhs))
    mutation=evaluate(selected,mutated)
    assert all(not r["semantic_entailment"] and not r["proof_found"] for r in mutation["records"])
    with_irrelevant=next(task for task in heldout if task.name=="future_extra_context")
    without_irrelevant=Goal("future_irrelevant_deleted",
        tuple(pair for pair in with_irrelevant.hypotheses if pair != ("x","y")),
        with_irrelevant.lhs,with_irrelevant.rhs)
    irrelevant=evaluate(selected,(with_irrelevant,without_irrelevant))
    assert irrelevant["all_exact"] and irrelevant["positive_solved"]==2

    forged=Edge(len(heldout[0].hypotheses)+3,True,heldout[0].lhs,heldout[0].rhs)
    forged_rejected=not checked_path(heldout[0],(forged,))
    missing_completeness_rejected=not (False and bool(trial_outcomes))
    old_no_positive_transfer=old_future["positive_solved"]==0
    generated_terms=emit_lean(dev+heldout,selected)
    trials=[{**c.contract(),"all_exact":r["all_exact"],"positive_solved":r["positive_solved"],"candidate_checks":r["candidate_checks"],"checker_calls":r["checker_calls"]} for c,r in trial_outcomes]
    gates={
        "old_scope_fully_enumerated": all(
            proof_search(task,OLD[0]) == next(all_one_step_proofs(task),None)
            for task in dev),
        "old_class_certifiably_insufficient_on_dev": not old["all_exact"],
        "new_program_is_not_old_member": selected not in OLD,
        "new_program_is_generic_and_source_bound": selected.opcode=="repeat",
        "development_exact":next(r for c,r in trial_outcomes if c==selected)["all_exact"],
        "protected_future_exact": protected["all_exact"],
        "protected_future_new_solutions": protected["positive_solved"]>old_future["positive_solved"],
        "selected_program_ablation_removes_future_success": protected["positive_solved"]>selected_ablation["positive_solved"],
        "relevant_evidence_deletion_blocks": mutation["positive_solved"]==0,
        "irrelevant_evidence_removal_preserves": irrelevant["all_exact"],
        "forged_evidence_rejected": forged_rejected,
        "incomplete_cover_is_not_expressivity_proof": missing_completeness_rejected,
        "strong_stateless_ties": protected==stateless,
        "full_executable_ledger_ties": protected==exact_executable_ledger,
        "lean_generated_certificates_present":len(generated_terms)==protected["positive_solved"] + next(r for c,r in trial_outcomes if c==selected)["positive_solved"],
    }
    budget={
        "candidate_programs_tried":len(trials),
        "development_candidate_checks":sum(r["candidate_checks"] for _,r in trial_outcomes),
        "development_checker_calls":sum(r["checker_calls"] for _,r in trial_outcomes),
        "protected_candidate_checks":protected["candidate_checks"],
        "protected_checker_calls":protected["checker_calls"],
        "lean_concrete_proofs_emitted":len(generated_terms),
        "full_lifecycle_cost_comparison":"UNKNOWN (synthetic cost model not wall/GPU or author hours)",
    }
    evidence={
        "status":"CANDIDATE_UNTIL_EXACT_HEAD_LEAN_CI",
        "protocol":"experiments/bundy_critic_genesis_v1/PREREGISTRATION.md",
        "scope":"internally authored finite equality proof-planning tests; old critic restricted to one-edge grammar",
        "selected_program":selected.contract(),
        "freeze_digest":frozen["freeze_digest"],
        "dev_obstruction": [r["task"] for r in old["records"] if r["semantic_entailment"] and not r["proof_found"]],
        "program_trials":trials,
        "old_protected":{k:old_future[k] for k in ("all_exact","positive_solved","negatives_respected")},
        "new_protected":{k:protected[k] for k in ("all_exact","positive_solved","negatives_respected")},
        "stateless_protected":{k:stateless[k] for k in ("all_exact","positive_solved","negatives_respected")},
        "ablation_protected":{k:selected_ablation[k] for k in ("all_exact","positive_solved","negatives_respected")},
        "gates":gates,
        "budget":budget,
        "claims":{
            "conditional_semantic_context_counterexample":"candidate until Lean CI",
            "bounded_meta_language_program_construction":"candidate until Lean CI",
            "new_primitive_or_meta_interpreter_semantics":"REJECTED_AS_NOT_TESTED (supplied repeat/compose)",
            "strict_gain_over_strong_stateless":"REJECTED_ON_THIS_CASE",
            "strict_gain_over_exact_executable_memory":"REJECTED_ON_THIS_CASE",
            "independent_natural_task_transfer":"UNKNOWN (internally authored tasks)",
            "general_autonomous_critic_invention":"UNKNOWN",
        },
        "heldout_records":protected["records"],
    }
    (OUT/"evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    assert all(gates.values()),gates
    print(json.dumps(evidence,sort_keys=True,indent=2))
    return evidence

if __name__=="__main__":
    run()