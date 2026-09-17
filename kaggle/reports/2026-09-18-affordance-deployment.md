# Deployed causal-affordance agent — measured results, 18 September 2026 NZ time

## Verdict

The deployment gap is fixed. The generated standalone MyAgent now instantiates ConsequenceController, vendors causal_affordance.py and consequence_controller.py, and records terminal feedback before reset. All 60 tests passed in the completed qualification.

The generated agent made measured progress on a real public diagnostic game: vc33-5430563c. With speculative cross-level transfer disabled, it completed Level 1 at interaction 64 and Level 2 at interaction 93, retaining two capability records. With transfer enabled, it completed only Level 1 within the same 400-interaction budget. The immutable baseline completed zero levels. Disabling only affordance ranking in the new transfer-enabled agent also produced zero levels.

This is public development-set evidence, not a sealed generalization result, a complete vc33 solve, a Kaggle score, or a competition submission. ft09 and ls20 still completed zero levels. The negative-transfer defect exposed by this experiment has been diagnosed but not fixed in this revision.

## Immutable evidence

- Tested branch: arc3-causal-affordance-v1.
- Tested candidate commit: 90b88081f8bd7c6c58dcd891b4654fc7f6d0169c.
- Frozen baseline commit: 846b3919f4b8cdf8e2ca414b41c7239c255419e7.
- [Completed run 35253430669](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35253430669).
- [Completed job 105311085166](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35253430669/job/105311085166).
- [Evidence artifact 10512072224](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35253430669/artifacts/10512072224).
- Artifact name: arc3-affordance-deployment; ZIP size: 570051 bytes.
- Artifact ZIP SHA256: 4ff0047fc5a983c5dc043f852801bb74932cda6f5a89df83a21ebcbfc7cd41aa.
- Candidate generated-agent SHA256: 37933991340b02c74d297545587c23e5d12f2a7f2ba20edfb35370072617a8c8.
- Baseline generated-agent SHA256: 871cd5b6092962b098d653875233d26098b84bf22c2ebe82f5750bf427264b5b.

The downloaded ZIP was independently hash-checked. Its candidate rebuilt byte-for-byte from the bundled modular sources. The full job logs were read and checked against the artifact results. The successful run occurred on 17 September UTC / 18 September New Zealand time. This report is a subsequent documentation-only commit, not the tested source revision.

## What changed and what was tested

The adapter now uses ConsequenceController rather than MemoryGraphController. The builder concatenates memory_graph, runtime, memory_controller, causal_affordance, consequence_controller and agent_template in dependency order, strips only explicitly vendored internal imports, and embeds hashes of all six source files.

GAME_OVER records its final observed effect and exact failed prefix before clearing the episode. WIN feedback can be consumed by is_done without buying an additional action. Full reset preserves purchased memory while preventing a fabricated transition across reset.

Seven new tests execute the generated code, substituting only the third-party SDK boundary. They check module inclusion, controller instantiation, nonterminal learning, terminal feedback, idempotent WIN handling, reset boundaries, and generated/modular decision equivalence. The red qualification at ded8b0f462b57f67cbddbb90d37b5a56c13996b8 exhibited the seven intended failures while the original 53 tests passed. The final CI run passed all 60 tests, built and compiled the standalone agent, built the offline CPU notebook, and separately instantiated the real SDK adapter with the correct controller.

The consequence-acquisition and affordance-scoring algorithms themselves remained unchanged from 8b4ede84c9f9b070213391a9127289b5668d6215 during this deployment comparison. The tested changes connect the existing mechanism to actual execution rather than tune it against the resulting game traces.

## Matched protocol

SDK pins: arc-agi 0.9.9 and arcengine 0.9.3. Framework pin: arcprize/ARC-AGI-3-Agents at 4743e7d0aaae0ded0d98a89a7e282e63564cd58b. Fixture repository pin: arcprize/ARC-AGI at f12822c4d550121c35a275008d964afbbed47d2f. Resolved transitive dependencies are saved in the artifact, not claimed to have all been version-pinned in advance.

There are 36 completed trials: 27 public trials over three real games and nine trials over one SDK fixture. These are not 36 independent games. One seed, 0, was used because the previous two-seed diagnostic produced duplicate deterministic behavior. Each cell starts with a fresh process, environment and agent.

The baseline and candidate each run four arms over the four worlds: full, no_refutation, no_transfer and neither. no_refutation disables exact-trie pruning, not all memory. no_transfer disables speculative cross-level programs, not same-level retained replay or capability recording. Four additional cells disable only affordance ranking in the candidate while keeping its other mechanisms, including transfer, enabled.

Public budgets are 400 interactions and the fixture budget is 128. Counts include the implicit construction RESET and every subsequent environment call, including RESET. All 36 cells ended in WIN or ACTION_BOUND, with no ERROR or TIMEOUT. Downloaded traces were checked for actions = trace length + 1 and environment_step_calls = trace length. All paired initial observation digests, game-file manifests and action limits matched.

Archived fixture programs were disabled in every evaluated cell. The trusted evaluator owns the environment; the policy receives public observations, a generic game label and no environment object. Execution uses offline SDK mode and Python socket guards after preparation, not an operating-system isolation guarantee. No Kaggle submission or actual Kaggle notebook execution was performed. The original integration branch and main were not modified by this work.

## Real public diagnostic results

All entries below use a 400-interaction limit. Values are maximum completed levels, not official scores.

| Exact game | Frozen baseline full | Candidate full | Candidate no_transfer | Candidate ranking disabled, transfer enabled |
|---|---:|---:|---:|---:|
| ft09-0d8bbf25 | 0 | 0 | 0 | 0 |
| ls20-9607627b | 0 | 0 | 0 | 0 |
| vc33-5430563c | 0 | 1 | 2 | 0 |

For vc33, both full and no_transfer completed Level 1 at cumulative interaction 64. no_transfer then completed Level 2 at interaction 93, 29 further interactions, and recorded two capabilities. It ended at Level 2, NOT_FINISHED, at interaction 400. The full candidate ended at Level 1, NOT_FINISHED, with one capability. The neither arm also reached two levels at 64 and 93. Removing only refutation made no behavioral difference to the corresponding candidate arm in any of these four worlds under these bounds.

The ranking-disabled vc33 cell completed no level and acquired no capability. Because the full and ranking-disabled cells differ only in that score override, this establishes a bounded causal contribution from ranking to the observed first success in this particular transfer-enabled comparison. No ranking-disabled plus transfer-disabled cell was run, and no claim is made about that unmeasured interaction or universal necessity.

Other observable differences are diagnostic, not success claims:

| Exact game | Baseline distinct observations | Candidate full distinct observations | Baseline steps with no immediate observation change | Candidate full steps with no immediate observation change |
|---|---:|---:|---:|---:|
| ft09-0d8bbf25 | 34 | 87 | 364/399 | 281/399 |
| ls20-9607627b | 329 | 355 | 0/399 | 9/399 |
| vc33-5430563c | 119 | 212 | 0/399 | 0/399 |

The new policy changes behavior in all three public games. More distinct observations or more visible changes alone do not establish useful learning. Unchanged observations do not prove an absence of hidden or delayed effects.

## Negative transfer: the next concrete defect

In vc33 full, after the first success at interaction 64, the policy spent 317 of the remaining 336 interactions on speculative transfer, approximately 94.3%. The trace contains repeated 24-action transfer blocks, with only sparse acquisition and reset actions between them. Disabling speculative transfer allowed Level 2 by interaction 93 within the same overall budget.

Source inspection identifies a specific relaunch problem in MemoryGraphController._next_transfer and _start_transfer. Exhausting an expanded program clears the active transfer and yields one non-transfer opportunity. A later call can immediately start the same retained source program again because there is no persistent record that this bounded proposal already used its trial budget in the target level. Individual proposals are bounded; their cumulative relaunch cost is not effectively bounded. The macro can therefore crowd out discovery after the first win.

This result supports a target-scoped transfer admission and trial-budget mechanism, not deletion of transfer everywhere. A bounded attempt ending without progress should expire as an unconfirmed proposal, not be promoted to a universal refutation. Further extension or readmission should require relevant evidence; acquisition needs a protected budget. This is the next proposed change and is NOT implemented by the tested revision.

## SDK fixture control — not benchmark evidence

Fixture: bt11-fd9df0622a1a, maximum 128 interactions, all archived solutions disabled.

| Configuration | Completed levels | Interactions | Outcome |
|---|---:|---:|---|
| Frozen baseline full | 5 | 98 | WIN |
| Candidate full | 5 | 73 | WIN |
| Candidate no_refutation | 5 | 73 | WIN |
| Candidate no_transfer | 2 | 128 | ACTION_BOUND |
| Candidate neither | 2 | 128 | ACTION_BOUND |
| Candidate ranking disabled, transfer enabled | 5 | 73 | WIN |

The candidate full milestones are 5, 13, 29, 49 and 73 cumulative interactions, with no terminal failures and no explicit RESET beyond construction. Its ranking-disabled counterpart has the same action/observation trajectory. Therefore the 98-to-73 improvement must not be attributed specifically to affordance ranking; it belongs to the broader deployed consequence-acquisition policy relative to the frozen baseline. Transfer remains beneficial in this narrow repeated-action world, which is why globally disabling it would be an unjustified general solution.

The audit stops immediately when the environment reports final WIN, before policy.is_done consumes that final observation. Thus its recorded capability count is four, not five. The adapter's final-WIN feedback path is separately verified by the executed deployment test; do not claim five serialized capability records from this fixture run.

## Metadata guard recovery

The initial deployment run 35252890728 passed the 60 tests and SDK checks but stopped before game evaluation because the downloaded metadata hashes differed from the historical audit. All three exact public IDs and all three game Python-source hashes matched the historical source pins.

The corrected workflow retains those historical game-source pins, freezes the newly downloaded metadata once, and checks every source and metadata file against that same manifest in every candidate and baseline cell. It records historical/current metadata hashes and saves current metadata bytes in deployment/paired-metadata. Metadata contains download-specific fields, but no claim is made that these are the only semantic differences from the historical metadata. As an additional check, the newly rerun baseline full action/observation traces match the historical baseline full traces for all four worlds.

The code-source pins remain:

- ft09.py: aa5b54f48a29da9f276c3df0dc04de728002f523384ab868c85d56d819cd0783.
- ls20.py: 298c810da2850d557c95d92a2cbd846df29a45d7134e20888617bedf5dafcd92.
- vc33.py: 8afa9f55054b2a2460b6c44ec5c66e120f6d6f4c2289e24d50832a68d1e3fcfd.

## Boundaries on interpretation

These three games have already been used as public development diagnostics. Generalization to sealed or hidden games remains unmeasured. No complete real public game was won in this run. Two other public games still have zero levels under the tested budget.

The affordance score is a heuristic based on repeated visual-effect signatures and spatial directness. It is not a complete causal model, learned goal relation, or verified behavioral quotient. Parameter-equivalence and reversible-pair helper tests do not establish that those helpers are used by the deployed selection path. The new effect/affordance state survives in-memory episode resets; existing canonical restart tests cover core ArcMemoryGraph records, not serialization of every new controller data structure.

The 400-action cutoff is bounded failure, not exhaustive search, a proof of expressive impossibility, or a NoResolution certificate. The useful finding is narrower: the deployed mechanism can now obtain first success in vc33, and the existing speculative-transfer policy can subsequently suppress further acquisition. Preserve the evidence and fix that measured interference before adding more macro composition.
