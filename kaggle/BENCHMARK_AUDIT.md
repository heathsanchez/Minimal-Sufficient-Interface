# Frozen ARC3 public diagnostic

The protected integration baseline is `846b3919f4b8cdf8e2ca414b41c7239c255419e7`.
This branch adds evaluation, not intelligence changes. The workflow verifies
that runtime sources, builder and provenance are unchanged.

`bt11` and `bt33` under `test_environment_files` are SDK fixtures. They MUST NOT
be reported as ARC-AGI-3 competition or held-out benchmark results. Earlier work
in this lineage mislabeled them. The fixture control is explicitly separated.

## Experiment fixed before running

Use the official SDK's anonymous catalog to obtain `ls20`, `ft09` and `vc33`.
The evaluator saves full version IDs, file hashes and generated-agent SHA256
BEFORE any evaluated policy acts. No benchmark source is given to the policy.
These are public diagnostics, not sealed holdouts: prior exposure elsewhere in
the programme is not ruled out. No mechanism is tuned against this suite here.

Each game/seed/arm runs in a fresh Python process, with a fresh agent and local
environment. Benchmark seeds are 0 and 1. Matching initial observation hashes
are required within each four-arm comparison; duplicate hashes across seeds
must not be interpreted as independent environments. Offline mode plus Python
socket guards prohibit ordinary network use during evaluation. This is not an
OS isolation guarantee. The agent has no environment object, only public frames.

The 2x2 arms are `full`, `no_refutation`, `no_transfer`, `neither`. Refutation
ablation disables trie-based next-action pruning, not all memory. Transfer
ablation disables speculative cross-level program reuse. Same-level retained
replay and least-visited exploration stay enabled in every arm. All archived
fixture programs are disabled. This prevents archive replay from masquerading
as acquisition and isolates the two mechanisms rather than changing everything.

The public budget is exactly 400 environment interactions per cell, INCLUDING
one implicit construction RESET and all explicit RESETs. The fixture control
has a 128-action budget. Failed environment calls are charged. Pure computation
is measured separately. A 30-second loop limit and 45-second process timeout
are safeguards, not evidence of expressive inadequacy. No artificial cutoff is
passed to the agent as GAME_OVER. All failures and incomplete cells are reported;
missing/unmatched/error cells cannot certify a valid comparison.

Metrics include levels, WIN, milestone action counts, attempts, resets, repeated
exact failed experiments, unchanged observations, distinct observation hashes,
action source counts and retained memory counts. Raw trajectories contain hashes
and actions, not source code. No SDK score is advertised as a Kaggle score.

## Reproduction

Run the `ARC3 frozen public benchmark audit` workflow on this branch. It builds
the same standalone `MyAgent`, runs all contracts, executes the fixture control,
and then the separate public diagnostics. The artifact contains locked manifests,
per-cell traces, comparison summaries and the unchanged generated agent/notebook.

A zero-solve result is valid experimental evidence, not a green competence gate.
An inaccessible catalog is a setup failure, not zero performance. All source
changes must be qualified on a new baseline and then tested prospectively on
new tasks; these diagnostics cannot subsequently be called untouched holdouts.
