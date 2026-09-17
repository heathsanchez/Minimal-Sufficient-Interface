# Frozen public ARC3 audit — measured results, 17 September 2026

## Verdict

The evaluation pipeline passed, but the frozen agent completed zero levels in all 24 public diagnostic trials. The same agent's SDK fixture control established a narrow causal benefit from exact refutation and cross-level program transfer. These are separate findings. This is not a hidden evaluation, a Kaggle submission, or evidence of competitive ARC-AGI-3 performance.

## Immutable evidence

- Tested audit commit: `fa4fc09717321a5ac5becc76b7cad6a2efb0b205`.
- Frozen controller/build baseline: `846b3919f4b8cdf8e2ca414b41c7239c255419e7`.
- Generated agent SHA256: `871cd5b6092962b098d653875233d26098b84bf22c2ebe82f5750bf427264b5b`.
- [Successful run 35201340787](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35201340787).
- [Full job logs, job 105136557756](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35201340787/job/105136557756).
- [Raw evidence artifact 10487917546](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35201340787/artifacts/10487917546).
- Artifact ZIP SHA256: `cbceeb4503b7bfe1888d290837383dac2ec9d7c6a068829901fcecc0ba8dd800`.

The job passed 46/46 tests, the frozen-source comparison, standalone-agent compilation, notebook generation, fixture evaluation and public evaluation. Downloaded artifact bytes were separately hash-checked. Its generated agent is byte-for-byte identical to the earlier successful integration bundle from run 35193050114. The original integration branch was not changed by this audit. No Kaggle submission was performed.

## Protocol fixed before evaluation

Public games were obtained through the official SDK. Full version IDs, source file hashes and the generated-agent hash were recorded before evaluated policy actions. SDK fixtures were separately labelled and cannot be accepted as benchmark games by the manifest validator.

Each trial used a fresh process, environment and agent. Every arm disabled archived fixture programs. The 2x2 arms were:

- `full`: refutation pruning and prospective cross-level transfer enabled.
- `no_refutation`: trie-based action pruning disabled; this is NOT removal of all memory.
- `no_transfer`: speculative cross-level program reuse disabled.
- `neither`: both disabled.

Same-level retained replay and least-visited exploration were held fixed across arms. Public observations, not game source, game-specific solution prefixes, or an environment object, were passed to the agent. The trusted evaluator retained the environment. Offline SDK mode and Python socket guards were used after preparation; this is not an operating-system sandbox guarantee.

Public trials used seeds 0 and 1, with an exact 400-interaction limit. The count includes the implicit construction RESET and every explicit RESET. Each completed public trial made 399 env.step calls. A time or action cutoff is not recorded as a GAME_OVER or proof of impossibility. Three setup RESETs used to download public environments were separately recorded, excluded from the policy trials, and supplied no learning data.

These are public diagnostics, not sealed holdouts. Earlier exposure elsewhere in the programme is not ruled out. No controller changes were made against these results during this audit.

## Actual public-game results

| Exact game | Levels completed | Budget consumed per trial | Distinct observed frames/states | Explicit RESETs | Steps with no immediate observation change |
|---|---:|---:|---:|---:|---:|
| `ft09-0d8bbf25` | 0 | 400 | 34 | 0 | 364/399 |
| `ls20-9607627b` | 0 | 400 | 329 | 3 | 0/399 |
| `vc33-5430563c` | 0 | 400 | 119 | 7 | 0/399 |

Every one of the 24 trials ended at ACTION_BOUND, not ERROR or TIMEOUT. Every trial had zero capability records and zero transfer actions. The comparison report returned MATCHED; each four-arm group had the same initial observation hash.

A separate full-artifact check compared the per-step action, source, before/after observation hashes, level and terminal-state records. For each game, all eight traces (four arms times two seeds) were identical. Thus these seeds did not generate independent behavioural test cases here, and 24 trials must not be described as 24 games or six independent scenarios.

For ft09, 91.23% of env.step calls caused no immediate change in the recorded public observation. This is not proof that those actions had no hidden or delayed effect. Conversely, ls20 produced 329 distinct observations without progress: observation novelty alone was not sufficient.

## SDK fixture causal control — not benchmark evidence

Pinned fixture: `bt11-fd9df0622a1a`, seed 0, maximum 128 interactions. All arms started from the same public observation and used the same generated agent with archived programs disabled.

| Arm | Maximum levels reached | Interactions | Outcome | Duplicate exact failed experiments |
|---|---:|---:|---|---:|
| full | 5 | 98 | WIN | 0 |
| no_refutation | 0 | 128 | ACTION_BOUND | 24 |
| no_transfer | 1 | 128 | ACTION_BOUND | 0 |
| neither | 0 | 128 | ACTION_BOUND | 24 |

The full agent's level milestones were 30, 38, 54, 74 and 98 cumulative interactions. The earlier report of 97 counted explicit step calls only; the new count includes one implicit startup RESET. The full trial had five explicit RESETs, five terminal failures, 25 exploration actions, 67 transfer actions and four retained capability records. It stopped at WIN before processing that last observation back into the controller, so do not claim five serialized capability records.

Within this fixture and budget, removing refutation prevented the first success, while removing transfer left only one level completed. This is matched causal evidence for the two mechanisms in this narrow test world; it does not establish transfer to real benchmark tasks.

## Source-level diagnosis and a separate synthetic diagnostic

At the frozen baseline, `OnlineController._exploration_guard` uses completed-level count, state, legal action IDs and image dimensions. It includes the image digest only after an archived capability completes. Generic action selection is least-visited within that coarse bucket. Its progress retention is triggered by a level increment; MemoryGraphController's hard refutations are triggered by terminal failure.

Reference: [frozen runtime.py](https://github.com/heathsanchez/Minimal-Sufficient-Interface/blob/846b3919f4b8cdf8e2ca414b41c7239c255419e7/kaggle/src/metalogic_arc3/runtime.py).

A local synthetic sensitivity diagnostic used controller code from the hash-verified generated agent, without the ARC adapter or external framework imports. Four differing 8x8 image streams, 32 turns each, held level, nonterminal state, legal actions (3,4) and dimensions fixed. No archived or prior capability was provided. All four produced the same alternating 3,4 sequence. This is a controller diagnostic, not additional ARC benchmark evidence.

Interpretation: the current agent can remember exact failures and reuse successes, but its first-success exploration does not use action-conditioned nonterminal visual consequences. On the real diagnostic games, it never obtained the initial success needed to activate transfer. Even where terminal failures occurred, trie pruning did not alter the measured trajectory. The coarse exploration key is not a demonstrated behavioural quotient: grouping images this way does not establish that they have equivalent winning continuations.

## Next implementation target — not implemented by this audit

Introduce a bounded observer of nonterminal action consequences before adding more capability composition. Distinguish measured effects from hypotheses: record what changed, in which observed context, following which action; let this evidence affect the next probe before any reward. Context conflicts should preserve separating histories rather than silently merge them. An unchanged frame must not be turned into a universal no-op rule.

First qualify this mechanism on controlled worlds that require different interventions under different observed states, with misleading visual novelty and delayed-effect controls. Then compare frozen versions at equal action budgets and reserve genuinely new tasks for prospective validation. Continued tuning on these three public games must be labelled development-set tuning.

The 400-action failures do not establish search completeness or expressive impossibility. They identify a practical acquisition bottleneck, not a certified NoResolution theorem and not a refutation of the wider RealityGraph/MSI programme.
