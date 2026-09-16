# ARC3 Kaggle Integration Design

Date: 2026-09-17

## Goal

Produce one self-contained ARC-AGI-3 Kaggle execution bundle from the existing verified MSI ARC3 lineage. GitHub remains the source of truth; Kaggle is only the offline execution shell.

## Starting point

Branch `arc3-kaggle-integration-v1` starts from `experiment/unified-arc3-multilevel-v1` at `ef718042107d054b175ee62ef2b332eae9218dc0`.

The initial runtime reuses the already-qualified ARC3 ideas rather than inventing a new architecture:

- public observation normalization from the frozen ARC3 controller;
- generic public action grounding, including parameterized ACTION6 coordinates;
- bounded consequence/residual learning;
- replay-derived retained programs/options;
- multilevel continuation and compositional reuse;
- minimum GOAL-sufficient state rather than full environmental reconstruction.

RealityGraph language growth is not placed in the first hot path. It remains an escalation layer for a later, certified expressive-inadequacy residual.

## Production/runtime split

### Development and qualification

Development may use:

- fresh offline ARC environments;
- replay;
- Lean promotion gates;
- ablation and matched controls;
- historical evidence and pinned source hashes.

### Kaggle runtime

The submitted agent must not require:

- network access;
- repository checkout;
- subprocess Lean;
- external model/API calls;
- creation of additional hidden evaluation environments.

It receives only the competition framework's live `frames` and `latest_frame`, updates persistent in-process state, and returns one legal `GameAction`.

## Runtime architecture

`MyAgent` owns a persistent `OnlineController`.

For each call:

1. Normalize `latest_frame` into a canonical public observation.
2. If a previous action exists, record the witnessed transition and public consequence.
3. Update the minimum currently warranted state key from consequence-relevant public features/history.
4. Prefer a previously witnessed retained continuation when its guard matches the current state.
5. Otherwise choose the least-tested legal action for the current state.
6. For complex ACTION6, choose a deterministic coordinate from a bounded coarse-to-fine public grid.
7. On progress, retain the successful suffix as a provisional reusable option.
8. On GAME_OVER or NOT_PLAYED, issue RESET while preserving cross-attempt retained options and clearing episode-local trajectory state.
9. On WIN, stop.

The first version intentionally does not claim transfer of a retained option across unrelated states. Guard mismatch falls back to exploration.

## Minimum-sufficient state policy

The state representation is deliberately conservative and task-directed:

- public `levels_completed`;
- public `state`;
- public available actions;
- compact frame fingerprint / bounded public frame statistics;
- bounded recent action history when needed to distinguish witnessed consequences.

No semantic labels such as player, key, door, goal, timer, or game-specific object names are supplied.

## Kaggle packaging

Create a `kaggle/` subtree with:

- `agent/my_agent.py`: self-contained generated submission source;
- `src/metalogic_arc3/`: readable modular development sources;
- `scripts/build_agent.py`: deterministic compiler from modular source to one self-contained agent file;
- `scripts/build_notebook.py`: official starter pattern, CPU accelerator, no internet;
- `notebooks/kernel-metadata.json`: Kaggle kernel metadata template;
- `Makefile`: setup, test, build-agent, notebook, submit, status;
- `.github/workflows/arc3-kaggle-integration.yml`: Python 3.12 qualification and notebook build;
- `provenance/sources.json`: pinned upstream/source identities;
- `tests/`: runtime and build contracts.

The generated notebook writes only the self-contained `my_agent.py` into the official ARC-AGI-3 Agents framework and lets the gateway produce `submission.parquet`.

## Source provenance

Initial provenance records:

- MSI integration base: `ef718042107d054b175ee62ef2b332eae9218dc0`;
- frozen ARC3 controller source commit: `68e37033f3ae1e86e992dfe8d982aef9133612aa`;
- verified shared transfer base: `ab32c4ba719e57d982c09c39ee921d33a7b7b33e`;
- ARC upstream used by the qualified transfer harness: `f12822c4d550121c35a275008d964afbbed47d2f`;
- official starter pattern: `arcprize/ARC-AGI-3-Kaggle-Starter` current source inspected on 2026-09-17.

## Success criteria

The integration is ready for first Kaggle execution when all of the following hold:

1. Runtime unit tests pass under Python 3.12.
2. `MyAgent` resets on NOT_PLAYED/GAME_OVER and stops on WIN.
3. Simple actions are deterministic and legal.
4. Complex action data is deterministic and bounded by observed frame dimensions.
5. A witnessed progress suffix becomes reusable only under a matching guard.
6. Reset clears episode-local state without deleting retained options.
7. Generated `agent/my_agent.py` contains no imports from local MSI/RealityGraph packages and no network/subprocess/model dependencies.
8. Notebook builder produces a valid offline CPU Kaggle notebook using the official competition gateway pattern.
9. CI builds the self-contained agent and notebook successfully.
10. No competition submission is made automatically; Kaggle token/account connection remains an explicit user-controlled final step.

## Claim boundary

This first bundle is an integration of already-earned ARC3 mechanisms into the Kaggle online interface. It does not yet claim that RealityGraph grammar growth is autonomously triggered online, that retained options transfer across arbitrary games, or that the resulting agent is leaderboard-optimal. Those are subsequent experimentally gated upgrades.