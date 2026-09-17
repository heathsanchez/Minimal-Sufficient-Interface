# MG-ARC4: target-scoped transfer contracts — measured results, 18 September 2026 NZ time

## Verdict

The cumulative speculative-transfer relaunch defect is fixed under an explicit per-target action allowance. The full generated agent now completes two vc33 levels at interactions 64 and 109, instead of the previous deployed agent's one level within 400 interactions. Its speculative transfer calls fall from 317 to 56. The bt11 SDK fixture remains a five-level WIN in 73 interactions.

This is an improvement to the integrated policy, not a new best vc33 timing: disabling speculative transfer still reaches the same two levels at 64 and 93. ft09 and ls20 remain at zero completed levels. These are public development diagnostics, not hidden generalization, complete public-game wins, or Kaggle scores.

The patch implements a resource/admission contract for unconfirmed reuse. It does not implement the full proposed calculus of certified source replacement, a QCK quotient, a new goal model, or a proof of source-target behavioral equivalence.

## Immutable evidence

- New branch: `arc3-contract-transfer-v1`.
- Tested candidate: `42dec1f23e243f9f3e288f57fc73833cde6c3c69`.
- Parent: `9406b0d96931e644429e8b3b547d57b9a7d08344`, the previous deployment report commit.
- Prior tested controller: `90b88081f8bd7c6c58dcd891b4654fc7f6d0169c`.
- [Successful run 35261773387](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35261773387).
- [Job 105338998548](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35261773387/job/105338998548).
- [Artifact 10514524958](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35261773387/artifacts/10514524958), named `arc3-contract-transfer`.
- Artifact ZIP: 508503 bytes, SHA256 `dbd51978c30e6787569d65546d1f8a9469b10382fb0a1c07a1c6efde33d49d05`.
- Candidate generated-agent SHA256: `1d9a3d9c130ee049e6428b6c87b80186756dead840086a6b68d7357960009000`.
- Prior generated-agent SHA256: `37933991340b02c74d297545587c23e5d12f2a7f2ba20edfb35370072617a8c8`.

The full job logs were read; 71/71 tests passed, the standalone agent compiled, the offline notebook built, and the paired diagnostic completed. The downloaded ZIP and both generated-agent hashes were independently checked. The candidate bytes match the locally rebuilt candidate. This report is a subsequent documentation-only commit, not the tested source revision.

Only the new branch was created and updated by this change. No merge, pull request, Kaggle submission, or actual Kaggle notebook execution was performed. The prior causal-affordance and original integration branches were not edited.

## What changed

Two production modules changed: memory_graph.py and memory_controller.py. The consequence/affordance selection algorithm, visual grounding, adapter and builder were left unchanged.

ArcMemoryGraph now serializes MG-ARC4 records for:

- the first admitted cumulative transfer limit for a target obligation;
- each source program's issued proposal count at that target;
- its OPEN, EXPIRED_UNCONFIRMED or WITNESSED_PROGRESS disposition.

Within one agent/game session, the current completed-level count names a target scheduling scope. This is deliberately not a claim that all images or histories at that level are behaviorally equivalent. Changing the raster, resetting an episode, loading serialized memory, or trying another source program does not provide a new aggregate allowance at that target.

The default inherited limit is 32 issued speculative actions per target. A completed bounded proposal expires without automatic relaunch. An interrupted proposal can consume only the remaining allowance; it cannot refund or replenish already issued slots. Increasing the runtime limit after a scope has started cannot increase that scope's recorded limit.

Proposal slots are charged conservatively before the final exact-trie filter. An issued action that is subsequently rejected by that filter is not refunded. Therefore actual speculative environment calls are no greater than the recorded issued count; the two counts need not always be equal. All source programs share the same target cap, preventing evasion through a different macro.

Exhaustion is recorded as EXPIRED_UNCONFIRMED. It does not add an entry to semantic refutations, erase the successful source witness, or manufacture target success. An actual observed level increment continues to earn a source-scoped capability record and opens a distinct next-level scheduling scope. Existing primitive-by-primitive observation, legality and exact-refutation checks remain in place.

MG-ARC3 memory remains loadable. Migration adds no fabricated target trial evidence. Parsing rejects malformed limits, unsupported source programs, duplicate trial records, invalid statuses, and aggregate overspend. This is structural record validation, not cryptographic authentication of the history.

There is no new same-target evidence-based readmission mechanism in this patch. Expired proposals are not requalified by arbitrary visual novelty. The choice of 32 is an inherited engineering bound, not a proven optimum for prospective developmental cost.

## Tests

Eleven new tests cover exhaustion, reset persistence, serialized restart, changing rasters, aggregate accounting across source programs, unconfirmed rather than refuted expiry, real level-boundary renewal, the actual generated adapter, non-increasing started limits, malformed ledgers and legacy loading. Two existing version-string assertions were updated from MG-ARC3 to MG-ARC4; their semantic assertions were preserved.

Nine initial regression tests were observed failing against the previous behavior before the production fix; two further parser/migration tests were then added. The local artifact-based test run passed 69 available tests. The downloaded source bundle omitted workflow YAML, so its two workflow-source checks were excluded only from that local runner. The remote full repository ran all 71 tests and passed, including those workflow checks.

A separate local synthetic stress diagnostic checked 240 reset/restart cases and 19200 decisions with varying caps and level boundaries. Transfer counts did not exceed the corresponding target allowance. This is additional bounded invariant testing, not ARC-solving or universal-equivalence evidence, and it is not an additional CI benchmark suite.

## Matched measurement protocol

There are 16 completed cells: three public games plus one SDK fixture, each under four configurations. That is twelve public cells and four fixture cells, not sixteen independent games.

Configurations are the new candidate; the previous deployed agent; the new candidate with speculative transfer disabled; and the new candidate with only affordance ranking disabled. These controls are not a complete factorial experiment over both switches. Same-level retained replay, capability recording and exact failure memory are not disabled by the no_transfer configuration.

Each cell uses a fresh process, agent and environment at seed 0. Public cells have a 400-interaction limit; the fixture has a 128-interaction limit. Counts include the implicit construction RESET and every explicit environment call. All cells finish as WIN or ACTION_BOUND, not ERROR, TIME_BOUND or TIMEOUT.

SDK pins are arc-agi 0.9.9 and arcengine 0.9.3. The agent framework is pinned to arcprize/ARC-AGI-3-Agents commit 4743e7d0aaae0ded0d98a89a7e282e63564cd58b; the fixture repository is pinned to arcprize/ARC-AGI commit f12822c4d550121c35a275008d964afbbed47d2f. Resolved transitive dependencies are saved, not all claimed pinned in advance.

Public source files retain the historical byte hashes. Metadata is downloaded once and the same source/metadata manifest is checked for every paired policy. Initial observation hashes match across all four configurations in every world. The policy receives public observations, a generic game label and no environment object; archived fixture programs are disabled. Evaluation uses offline SDK mode and Python socket guards after preparation, not an OS isolation guarantee.

## Actual results

Maximum completed levels under the stated budgets:

| World | Prior deployed | MG-ARC4 candidate | Candidate no_transfer | Candidate no_affordance |
|---|---:|---:|---:|---:|
| ft09-0d8bbf25, public, 400 | 0 | 0 | 0 | 0 |
| ls20-9607627b, public, 400 | 0 | 0 | 0 | 0 |
| vc33-5430563c, public, 400 | 1 | 2 | 2 | 0 |
| bt11-fd9df0622a1a, SDK fixture, 128 | 5 / WIN at 73 | 5 / WIN at 73 | 2 / bound at 128 | 5 / WIN at 73 |

### vc33

The prior, candidate and no_transfer configurations all complete Level 1 at cumulative interaction 64. The new full candidate completes Level 2 at interaction 109 and retains two capability records; the prior never completes Level 2 within 400. The candidate ends NOT_FINISHED with two completed levels, not a complete game win.

The new candidate uses 56 speculative transfer calls, versus 317 previously, a reduction of 261 calls. Its ledger issues 24 at target scope 1 (pursuing Level 2) and 32 at scope 2 (pursuing Level 3). Direct counting of the traces agrees with those scope totals.

Disabling speculative transfer remains faster: Level 2 at interaction 93, sixteen interactions before the capped candidate. Thus this change removes the measured runaway-relaunch failure while preserving beneficial transfer elsewhere; it does not establish optimal transfer admission or positive transfer on vc33 itself.

Disabling only affordance ranking yields no completed level and no acquired capability. This supports a bounded causal contribution of the ranking in this particular fixed agent and development world, not a universal necessity or a proven causal state model.

### bt11 and the other games

The fixture's prior, candidate and ranking-disabled policies all complete five levels at interactions 5, 13, 29, 49 and 73. The candidate still issues 67 transfer actions across distinct targets and has no explicit reset or terminal failure. Its per-target issuance is 8, 16, 20 and 23. The audit stops on final WIN before the adapter consumes that final observation, so the recorded capability count remains four, not five.

With transfer disabled the fixture reaches only two levels within 128 interactions. This is the positive control showing why globally deleting transfer is not the appropriate general repair.

The full candidate and prior have identical action/observation trajectories in ft09, ls20 and bt11. The two real games still fail to acquire a first successful capability, so transfer-budget management cannot fix their initial acquisition bottleneck.

## Independent artifact checks

All sixteen rows were checked for actions = trace length + 1 and environment_step_calls = trace length. The four starts per world, game manifests and action limits match. Candidate issued totals and independently counted transfer calls respect the per-target limit.

The prior action/observation traces reproduce the previously qualified deployment artifact for all four worlds. The candidate no_transfer traces also reproduce that earlier no_transfer control for all four worlds. These comparisons ignore memory-format hashes and compare actions, resulting observation hashes, completed levels and terminal states.

## Architectural interpretation and remaining limits

The implementation now separates a witnessed source program from permission to spend target actions on it. A source success is not a target substitution certificate, and an execution allowance is not a semantic theorem. Those two forms of authority must remain separate.

The supplied certified-substitution synthesis motivates this distinction, but the wider QCK closure construction, assumptions checking, interaction-contract composition and recoverability accounting are not implemented here. This patch does not prove any two ARC histories have identical futures, does not serialize every EffectMemory/AffordanceMemory structure, and does not make provenance reconstructive. A hash cannot recover discarded state.

The next unresolved engineering question is applicability: which part of a source capability is relevant at a new target, and what evidence should justify a bounded continuation or requalification? A fixed cap controls damage but does not answer that semantic question. The sixteen-interaction deficit against no_transfer in vc33 makes that limitation measurable.

The reported tests establish bounded functional behavior, not universal soundness for arbitrary unmodeled worlds. Public development-set tuning remains public development-set tuning. Generalization to sealed or private games remains unmeasured, ft09 and ls20 remain unsolved under these bounds, and neither an action cutoff nor an expired proposal is a NoResolution certificate.
