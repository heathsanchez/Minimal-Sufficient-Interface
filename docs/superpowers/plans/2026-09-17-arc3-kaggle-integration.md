# ARC3 Kaggle Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one self-contained, offline ARC-AGI-3 Kaggle agent bundle from the existing MSI ARC3 lineage and verify that GitHub CI can generate the exact submission notebook.

**Architecture:** Keep the readable runtime modular under `kaggle/src/metalogic_arc3`, compile it deterministically into a single `kaggle/agent/my_agent.py`, and splice that file into the official Kaggle notebook pattern. The live runtime is online/persistent and consequence-driven; replay, Lean, extra environment creation, and model/API calls remain outside the Kaggle hot path.

**Tech Stack:** Python 3.12, stdlib-only runtime, `arcengine`/ARC-AGI-3 Agents framework at execution time, `unittest`, GitHub Actions, Kaggle CLI for the final user-controlled push.

**Spec:** `docs/superpowers/specs/2026-09-17-arc3-kaggle-integration-design.md`

## Global Constraints

- Kaggle runtime must be offline and CPU-only for V1.
- Runtime must not import MSI, RealityGraph, MathGraph, requests, OpenAI clients, or subprocess.
- Runtime must not create secondary hidden evaluation environments.
- No game-specific winning sequence, object label, or solved prefix may be embedded.
- A retained option is reusable only under a matching observed guard.
- Reset clears episode-local trajectory state but preserves retained options.
- Submission is never auto-triggered from CI.

---

### Task 1: Runtime contracts

**Files:**
- Create: `kaggle/tests/test_runtime.py`
- Create: `.github/workflows/arc3-kaggle-integration.yml`

**Interfaces:**
- Consumes: none.
- Produces: failing tests defining `OnlineController`, `normalize_frame`, `ActionToken`, and runtime reset/progress semantics.

- [ ] **Step 1: Write failing tests**

Tests cover deterministic exploration, progress retention, guard-scoped option reuse, reset preservation, and complex coordinate bounds using pure fake frames.

- [ ] **Step 2: Run CI and verify RED**

Expected: import failure for `kaggle/src/metalogic_arc3/runtime.py` or missing `OnlineController`.

- [ ] **Step 3: Commit failing contracts**

Commit only tests/workflow.

### Task 2: Minimal online runtime

**Files:**
- Create: `kaggle/src/metalogic_arc3/runtime.py`
- Create: `kaggle/src/metalogic_arc3/__init__.py`

**Interfaces:**
- Produces:
  - `normalize_frame(frame) -> Observation`
  - `ActionToken(action_id: int, x: int | None = None, y: int | None = None)`
  - `OnlineController(action_ids: tuple[int, ...], max_history: int = 8)`
  - `OnlineController.observe_and_choose(frame) -> ActionToken | None`
  - `OnlineController.reset_episode() -> None`

- [ ] **Step 1: Implement the minimum code required by Task 1**

State key is public consequence-directed data only: level, state, available actions, compact frame fingerprint, and bounded action history.

- [ ] **Step 2: Run CI and verify GREEN**

Expected: runtime tests pass.

- [ ] **Step 3: Refactor while green**

Keep runtime stdlib-only and deterministic.

### Task 3: ARC framework adapter

**Files:**
- Create: `kaggle/src/metalogic_arc3/agent_template.py`
- Create: `kaggle/tests/test_agent_source.py`

**Interfaces:**
- Consumes: `OnlineController`, `ActionToken`.
- Produces: `MyAgent(Agent)` with `is_done` and `choose_action` matching the official starter contract.

- [ ] **Step 1: Write failing source-level tests**

Verify source contains no forbidden imports/dependencies and exposes the required class/methods.

- [ ] **Step 2: Implement the adapter**

Convert `ActionToken` to `arcengine.GameAction`, issue RESET on NOT_PLAYED/GAME_OVER, and attach coordinate data for complex actions.

- [ ] **Step 3: Verify GREEN**

### Task 4: Deterministic single-file compiler

**Files:**
- Create: `kaggle/scripts/build_agent.py`
- Create: `kaggle/tests/test_build_agent.py`
- Generate: `kaggle/agent/my_agent.py`
- Create: `kaggle/provenance/sources.json`

**Interfaces:**
- `build_agent.py` concatenates the runtime and adapter into one import-clean source file and embeds a provenance dictionary.

- [ ] **Step 1: Write failing build test**

Assert two consecutive builds are byte-identical and generated source has no local-package imports.

- [ ] **Step 2: Implement compiler**

Use only Python stdlib. Strip package-relative imports from the adapter and prepend runtime source.

- [ ] **Step 3: Build twice and verify byte identity**

### Task 5: Kaggle notebook shell

**Files:**
- Create: `kaggle/scripts/build_notebook.py`
- Create: `kaggle/notebooks/kernel-metadata.json`
- Create: `kaggle/tests/test_notebook_build.py`
- Generate: `kaggle/notebooks/submission.ipynb`

**Interfaces:**
- Follows the official starter pattern: install wheel offline, write `/tmp/my_agent.py`, copy ARC-AGI-3-Agents, register `MyAgent`, point `.env` at `gateway`, execute framework, emit dummy parquet only outside competition rerun.

- [ ] **Step 1: Write failing notebook-structure test**

Assert CPU/no internet metadata and required gateway commands are present.

- [ ] **Step 2: Implement CPU notebook builder**

- [ ] **Step 3: Verify generated notebook contract**

### Task 6: One-command developer/Kaggle workflow

**Files:**
- Create: `kaggle/Makefile`
- Create: `kaggle/.gitignore`
- Create: `kaggle/README.md`
- Modify: `.github/workflows/arc3-kaggle-integration.yml`

**Interfaces:**
- Commands: `make test`, `make build-agent`, `make notebook`, `make submit`, `make status`.
- `make submit` requires `.kaggle/access_token` and a non-placeholder Kaggle username.

- [ ] **Step 1: Add workflow/build smoke tests**

- [ ] **Step 2: Add Makefile and concise operating README**

- [ ] **Step 3: CI runs full tests, builds agent and notebook, and uploads generated artifacts without submitting to Kaggle**

### Task 7: Final qualification

**Files:**
- No new production files unless verification exposes a defect.

- [ ] **Step 1: Run full GitHub Actions qualification**

Expected: all unit/source/build/notebook tests green.

- [ ] **Step 2: Inspect generated artifacts**

Confirm `my_agent.py` is self-contained and `submission.ipynb` is offline CPU.

- [ ] **Step 3: Record exact branch HEAD and run ID**

The final user-controlled step is adding their Kaggle token locally and invoking `make submit`; CI must not possess or require that token.