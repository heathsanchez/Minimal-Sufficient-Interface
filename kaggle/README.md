# Metalogic ARC3 Kaggle Integration

This directory is the single execution shell for the ARC-AGI-3 competition agent.

The readable source lives under `src/metalogic_arc3/`. `scripts/build_agent.py` compiles it deterministically into one self-contained `agent/my_agent.py`, and `scripts/build_notebook.py` places that exact file into an offline CPU Kaggle notebook using the official ARC-AGI-3 gateway pattern.

## Runtime boundary

The competition hot path is deliberately small:

```text
live public frame
  -> normalize observation
  -> record consequence of previous action
  -> update minimum warranted task state
  -> reuse a witnessed progress program only under a matching guard
  -> otherwise choose the least-tested legal public action
  -> return GameAction
```

The submitted runtime does **not** require network access, GitHub, Lean subprocesses, external model/API calls, or creation of extra hidden environments. Lean/replay/ablation remain development and qualification tools outside the Kaggle hot path.

## Get the integrated branch

```bash
git clone https://github.com/heathsanchez/Minimal-Sufficient-Interface.git
cd Minimal-Sufficient-Interface
git checkout arc3-kaggle-integration-v1
cd kaggle
```

## One-time local setup

```bash
make setup
```

This creates the Python 3.12 environment, installs ARC/Kaggle dependencies, clones the official `ARC-AGI-3-Agents` framework into `vendor/`, and slims its eager optional-agent imports exactly for this lightweight runtime.

Set your Kaggle notebook owner once by replacing `REPLACE_WITH_YOUR_USERNAME` in:

```text
notebooks/kernel-metadata.json
```

Create a Kaggle API token in Kaggle settings and save the token string locally as:

```text
.kaggle/access_token
```

That directory is gitignored. Do not commit the token.

## Verify locally on real ARC3 games

First run the repository contracts:

```bash
make test
```

Then run the generated agent through the same official agent framework used by the Kaggle shell:

```bash
make verify-local
```

For one game:

```bash
make play-local GAME=ls20
```

For all available games:

```bash
make play-local
```

To list game IDs:

```bash
make list-games
```

The first local ARC call may download/cache the public game source; subsequent local runs use the cache. The hidden Kaggle execution remains internet-disabled.

## Build the exact Kaggle artifact

```bash
make notebook
```

This produces:

```text
agent/my_agent.py
notebooks/submission.ipynb
```

Both are generated artifacts and are gitignored. The source-of-truth code remains modular and reviewable.

## Push to Kaggle

```bash
make submit
make status
```

`make submit` refuses to run if the token is missing or the Kaggle username placeholder is still present. This pushes the notebook for Kaggle's save/run phase; the deliberate competition submission of its `submission.parquet` remains a separate UI action. CI never submits to Kaggle and never needs the token.

## Provenance

`provenance/sources.json` pins the MSI ARC3 integration base, frozen ARC3 controller, verified shared-transfer checkpoint, and ARC upstream used by the qualified research lineage.

## V1 claim boundary

This bundle connects the existing consequence-driven ARC3 machinery to the official online Kaggle agent contract. It currently retains exact-guarded progress programs and uses deterministic bounded exploration. RealityGraph verified language growth is intentionally not in the first hot path; it should be added only after a live residual establishes that the present observation/action language is expressively inadequate rather than merely under-searched.
