# Prospective continuous two-repair qualification v1

Frozen before implementing or executing the qualification harness.

## Question

Can the existing bounded Austin development machinery operate in one process and one monotonically retained state across two different verified repairs, then use both retained repairs to change matched search on a later task not consulted during either repair?

This is a causal-lineage qualification of existing mechanisms, not a new kernel or an unrestricted self-development claim.

## Frozen source

- MSI base commit: `f70f92874c1c83edbc9912c0d1a9cbb77e9bb417` (`austin-capability-installation-v1`).
- Existing repair 1 implementation: `experiments/austin_capability_installation.py`.
- Existing repair 2 implementation: `experiments/austin_completion_development.py`.
- Existing frozen search adapter/controller: `experiments/austin_solver_core_ab.py`.
- External solver source repository: `heathsanchez/equational-theories-lean-stage2`.
- External solver commit: `10f49d22f4030c3925aa5b2633ed73fd10a78cff`.
- Solver blob: `05aa1c7d1d301d6d178b5ff9e1364cd41fe7fd3c` at `submissions/mathgraph/solver.py`.
- Python: 3.11.
- Lean: 4.24.0.

The three existing source modules above may be imported and orchestrated but not changed. Their source hashes will be recorded and checked by the harness.

## Frozen task stream

1. **Training task / repair 1 — constructor level.** Present `E40909` only to the existing capability developer. The root constructor is expected to leave a verified residual; the existing generic `contextual_transport` constructor may be proposed. It is retained only after independent Lean replay of the generated training certificate and exact proposal/certificate identity checks.
2. **Training task / repair 2 — completion level.** With repair 1 retained, derive the existing bounded critical-pair residual from `E40909`. The existing generic `critical_pair_join` constructor may be proposed. No target-specific completion equality is supplied. It is retained only after independent Lean replay of the generated `E40909` completion certificate and exact dependency/certificate checks.
3. **Later task — no development.** After both repair decisions are closed, reveal and run the fixed later source `E677`:
   `y ◇ (x ◇ ((y ◇ x) ◇ y)) = x`.
   No developer is called on this task. The retained generic constructors alone must derive a proof-carrying completion equality and pass independent replay before it can be supplied to the frozen search controller.

`E677` must not occur in repair selection, construction, ranking, certificates, or verification for tasks 1–2. Source inspection or execution of the later case after this preregistration is allowed; it may not cause changes to source modules, repair grammar, controller, budgets, or outcome criteria.

## Causal retention rule

For each repair:

`proposal from current state → independent certificate replay → exact readback/digest check → retention`.

A failed replay, stale or forged certificate, missing dependency, changed source hash, or changed base revision prevents retention and makes the qualification fail closed. The state passed to task 2 must be the exact retained output of task 1. The state passed to task 3 must be the exact retained output of task 2.

## Frozen budgets and matched controls

All later-search arms use the unchanged `run_core` controller and identical:

- wall budget: 10.0 seconds;
- term bound selected by the existing controller;
- maximum depth: 12;
- maximum rules: 1000;
- maximum rounds: 128;
- new clauses per round: 512;
- maximum clauses: 12000;
- normalization steps: 128;
- maximum proof nodes: 100000;
- deterministic `PYTHONHASHSEED=0`.

Arms, in frozen order:

1. `baseline`: original solver, no retained equality;
2. `retained`: exact independently replayed E677 equality derived using the two retained generic capabilities;
3. `remove_completion`: task-1 state only; no completion equality supplied;
4. `remove_transport`: remove task-1 capability while attempting to preserve task-2 state; the existing dependency verifier must reject this state, and search then runs without an equality;
5. `remove_all`: initial state; no equality.

The baseline, removal arms, and retained arm have identical search budgets. Any injected equality must report `injection_status=accepted`; otherwise the run is inconclusive.

## Decisive result criteria

`QUALIFIED_BOUNDED_CONTINUOUS_DEVELOPMENT` requires all of:

- two distinct proposal types are produced in order by the unchanged developers;
- task 2 consumes the exact retained task-1 state;
- each proposal is independently replayed before retention;
- the task-2 certificate depends on the exact retained task-1 certificate;
- E677 is absent from all task-1/task-2 evidence;
- no developer is invoked after E677 is revealed;
- the retained E677 proof and any solver proof replay independently in Lean;
- the retained arm differs from every removal arm on at least one preregistered search metric (`added_clauses`, `generated`, `active`, `pending`, `proof_nodes`, or replay success), without a larger budget;
- `baseline`, `remove_completion`, and `remove_all` agree exactly on replay status and deterministic search metrics;
- `remove_transport` rejects the invalid dependency and then agrees with baseline;
- exact source hashes, state digests, certificate digests, controller metrics, and replay markers are serialized.

If the retained arm does not change later search, the bounded qualification is negative. Timeout, source mismatch, replay failure, unsupported residual, infrastructure failure, or nondeterministic mismatch is `INCONCLUSIVE`, never a negative scientific result.

## Supplied boundary

The protected objective, E40909 verifier obligations, E677 later source, initial Python/Lean/solver substrate, the two meta-operations (`contextual_transport`, `critical_pair_join`), certificate interpreters, critical-pair machinery, and search controller are supplied. The repair grammar is therefore supplied. Intermediate obligations are computed by the existing residual procedures rather than named as target-specific E677 repairs. Success licenses only bounded verified selection/composition and causal retention within this supplied meta-language.
