# Minimal-Present Test 1 — Frozen Protocol

Status: PRE-REGISTERED / NOT YET RUN

This file and `minimal_present_controller_v1.py` are committed BEFORE any historical turning points are selected for Test 1.

## Frozen controller

File: `experiments/convergence/minimal_present_controller_v1.py`
SHA-256 (UTF-8 bytes): `3d5571716f70c47ad795538f0401f0ee45ba1c66ef9ce7f8af8d832f072b35b8`

The controller may read only these seven fields:

1. `completion_satisfied`
2. `verifier_status`
3. `scope_ok`
4. `attached`
5. `causal_status`
6. `live_residual`
7. `next_process_test`

It MUST NOT inspect parked results, branch names, commit messages, prose transcripts, future commits, or any later-selected test case identities.

## Non-circular case selection

After this freeze commit exists, candidate historical turning points are generated mechanically from commits strictly ancestral to the freeze commit. A commit is eligible iff:

- `program_frontier.json` exists at the commit and at its first parent; and
- either `last_transition.result_id` changes or `live_residual.text` changes relative to the first parent.

No semantic hand-picking is allowed.

If more than 20 candidates exist, rank each candidate by:

`SHA256(controller_sha256 + ":" + candidate_commit_sha)`

ascending lexicographically and take the first 20. If <=20 exist, use all.

The selection rule is frozen here before candidate identities are inspected.

## What Test 1 actually tests

A FULL-vs-MINIMAL comparison under a controller that is hard-coded to ignore history would be tautological. Therefore the empirical target is stronger and non-circular:

For each mechanically selected historical turning point:

1. Reconstruct the seven-field MINIMAL state from evidence available at that commit only.
2. Run the frozen controller.
3. Compare its predicted next intervention class to the actual next consequential transition recorded after that turning point, using a predeclared action-class mapping.
4. Separately compare with the repository's recorded historical route when available.
5. Ablate each populated minimal field one at a time; record whether the controller's consequential action changes and whether historical agreement is lost.

The strong compression claim survives only if the minimal controller predicts the consequential next-action class at high rate AND parked/full-history information is unnecessary for those decisions. No post-hoc controller edits are allowed after case identities are known.

## Action classes

Frozen output classes:

- `STOP`
- `RUN_VERIFIER`
- `REVERIFY_SAME_QUESTION`
- `CHECK_SCOPE`
- `CHECK_ATTACHMENT`
- `ABLATE_CAUSE`
- `EXECUTE_NEXT_PROCESS_TEST`
- `LOCALIZE_RESIDUAL`

Any historical transition that cannot be mapped without interpretation is scored `UNSCORABLE`, not force-fit.

## Acceptance / failure

This preregistration does NOT set a success threshold after seeing data. Report exact counts:

- exact action-class agreement / scorable cases;
- consequence-equivalent agreement / scorable cases;
- number of UNSCORABLE cases;
- per-field ablation sensitivity;
- every disagreement with commit IDs and evidence.

A single disagreement is evidence against the strongest claim that the frozen minimal present is universally sufficient. The result may still support a weaker bounded claim.

## Independence rule

The controller and selection rule are immutable for Test 1. Any repair after seeing selected cases creates `v2` and requires a fresh, disjoint holdout.
