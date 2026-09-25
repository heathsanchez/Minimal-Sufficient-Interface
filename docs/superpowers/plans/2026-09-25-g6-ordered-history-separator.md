# G6 Ordered-History Separator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and host-qualify the smallest zero-write G6 experiment that tests whether an earlier selector click survives a shared final selector state.

**Architecture:** A standalone experiment module reuses the qualified `enter_g6`, control discovery, and click functions.  It canonicalizes public observations, executes a complete two-pair × five-suffix census from fresh identical prefixes, classifies only a response separator or bounded negative, and emits a fail-closed evidence artifact.  A dedicated workflow runs the full regression suite, the exact public game, and an independent exact-head evidence seal.

**Tech Stack:** Python 3.12, `unittest`, existing Duck/ARC3 public harness, GitHub Actions, canonical JSON/digests.

**Spec:** `docs/superpowers/specs/2026-09-25-g6-ordered-history-separator.md`

## Global Constraints

- Exact public game is `tn36-ef4dde99`.
- Use the qualified G1→G5 entry path and common prefix `RRRRUULLUU`.
- Controlled histories are exactly `UL` versus `LL` and `LU` versus `UU`.
- Common suffix bank is exactly `("", "U", "D", "L", "R")`.
- Zero target writes, zero submit clicks, zero model calls, and zero source inspection.
- Maximum 13 clicks per trial.
- Unknown, malformed, drifted, or exceptional execution is `NON_EVIDENCE`, never a scientific rejection.
- No solver integration and no target-projection claim in this branch.

## Review Focus

- A changed first-intermediate frame must not by itself count as a separator; only the shared-endpoint frame or common-suffix response may separate.
- Two trials with different common-prefix observations must fail closed instead of being compared.
- A missing suffix or history pair must not be accepted as a complete negative.
- Semantic identity must be recomputed from meaning-bearing evidence rather than trusted from the artifact.
- Any target write, submit click, over-budget trial, model call, or source inspection must invalidate the scientific result.

---

### Task 1: Canonical observation and separator contracts

**Files:**
- Create: `experiments/arc3_public_g6_ordered_history_separator.py`
- Create: `kaggle/tests/test_g6_ordered_history_separator.py`

**Interfaces:**
- Consumes: `canonical_digest`, `_matrix`, `_source_bits`, and public frame metadata.
- Produces: `observation_record(prefix_matrix, frame, trace) -> dict`, `compare_trials(left, right) -> dict`, `_semantic_id(result) -> str`, and `validate_result(result, executing_head=...)`.

- [ ] **Step 1: Write failing canonical-observation tests**

  Add literal fixtures proving that `observation_record` records exact coordinate/value changes and that equal matrices produce equal digests independent of list/tuple container choice.  Add a test that changing one pixel changes both the digest and explicit change record.

  ```python
  def test_observation_records_exact_public_change():
      prefix = ((0, 0), (0, 0))
      frame = fake_frame(((0, 5), (0, 0)), bits=(1, 0, 0, 0, 0, 0))
      observed = observation_record(prefix, frame, ("U", "L"))
      assert observed["changes"] == [
          {"row": 0, "column": 1, "before": 0, "after": 5}
      ]
  ```

- [ ] **Step 2: Run the focused test and verify RED**

  Run: `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator -v`

  Expected: import failure because `arc3_public_g6_ordered_history_separator` does not exist.

- [ ] **Step 3: Implement minimal canonical observation code**

  Implement matrix normalization, exact diff extraction, source bits, public level/state, trace, and canonical digest.  Reject dimension mismatch and malformed source-bit arity.

- [ ] **Step 4: Add failing separator-boundary tests**

  Add literal trial fixtures proving:

  - different first-intermediate observations alone do not separate;
  - different shared-endpoint observations separate at suffix `""`;
  - equal endpoints but different `"R"` responses separate under `"R"`;
  - different endpoint controls are rejected rather than compared.

- [ ] **Step 5: Run the focused test and verify RED**

  Run: `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator -v`

  Expected: failures because `compare_trials` and evidence validation are absent.

- [ ] **Step 6: Implement minimal comparison and evidence validation**

  `compare_trials` must compare only `endpoint_observation` and
  `suffix_observation`, emit exact differing fields, and require identical
  endpoint labels, prefix digests, and suffixes.  `validate_result` must
  reconstruct the complete pair/suffix census, recompute every semantic ID,
  derive the classification from the comparisons, and enforce all global
  constraints.

- [ ] **Step 7: Run focused tests and full regression suite**

  Run:

  ```bash
  PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator -v
  PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v
  ```

  Expected: all focused tests pass; full suite passes with the new tests added to the 136-test baseline.

- [ ] **Step 8: Commit**

  ```bash
  git add experiments/arc3_public_g6_ordered_history_separator.py kaggle/tests/test_g6_ordered_history_separator.py
  git commit -m "Add G6 ordered-history separator contracts"
  ```

### Task 2: Exact public same-endpoint census

**Files:**
- Modify: `experiments/arc3_public_g6_ordered_history_separator.py`
- Modify: `kaggle/tests/test_g6_ordered_history_separator.py`

**Interfaces:**
- Consumes: Task 1 observation/comparison/validation functions and existing `enter_g6`, `_selector_controls`, and `click`.
- Produces: `run_trial(history, suffix, enter_g6=None) -> dict`, `build_result(enter_g6=None, head=None, runner=None) -> dict`, and CLI evidence output.

- [ ] **Step 1: Write failing executor tests with a complete deterministic fake environment**

  The fake must expose full public frame structure and record actual clicks.
  Test that each trial performs exactly the ten-click prefix, two-click history,
  and optional one-click suffix; never discovers or clicks the target panel or
  submit control; and retains first-intermediate, endpoint, and suffix records.

- [ ] **Step 2: Run the executor tests and verify RED**

  Run: `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator.OrderedHistoryExecutorContracts -v`

  Expected: failures because `run_trial` and `build_result` are absent.

- [ ] **Step 3: Implement the minimal executor and result builder**

  Re-enter G6 for every trial, verify level 5, discover controls dynamically,
  execute the exact common prefix/history/suffix trace, enforce the 13-click
  budget, and emit all ten trials.  Preserve completed trials and return
  `RESIDUAL/NON_EVIDENCE` on exceptions or prefix drift.  Derive
  `RESPONSE_SEPARATOR_ONLY` or `WARRANTED_NEGATIVE` only after the complete
  census validates.

- [ ] **Step 4: Add failure-path tests**

  Test incomplete census, inconsistent prefix digest, missing control,
  exception after completed trials, over-budget trial, target-write mutation,
  stale head, and stale semantic ID.  Each must fail closed or produce
  `NON_EVIDENCE` with completed evidence preserved.

- [ ] **Step 5: Run focused tests and full suite**

  Run:

  ```bash
  PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator -v
  PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v
  ```

  Expected: focused tests and the entire suite pass.

- [ ] **Step 6: Commit**

  ```bash
  git add experiments/arc3_public_g6_ordered_history_separator.py kaggle/tests/test_g6_ordered_history_separator.py
  git commit -m "Execute bounded G6 same-endpoint history census"
  ```

### Task 3: Hosted qualification and exact-head seal

**Files:**
- Create: `.github/workflows/arc3-public-g6-ordered-history-separator.yml`
- Modify: `kaggle/tests/test_g6_ordered_history_separator.py`

**Interfaces:**
- Consumes: Task 2 CLI and `validate_result`.
- Produces: exact public hosted result artifact and log for branch `arc3-public-g6-ordered-history-separator-v1`.

- [ ] **Step 1: Write the failing workflow contract test**

  Assert that the workflow is branch-scoped, pins Duck harness commit
  `7652836056c59e044f093e3c13ed7438c814169e`, downloads
  `tn36-ef4dde99`, runs the complete regression suite, executes the new CLI,
  validates with `GITHUB_SHA`, requires zero target writes, and always uploads
  the result plus log.

- [ ] **Step 2: Run the workflow contract test and verify RED**

  Run: `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator.HostedWorkflowContracts -v`

  Expected: failure because the workflow file does not exist.

- [ ] **Step 3: Implement the workflow**

  Mirror the qualified predecessor workflow's pinned environment.  Seal only
  `RESPONSE_SEPARATOR_ONLY` or `WARRANTED_NEGATIVE`; allow
  `RESIDUAL/NON_EVIDENCE` to upload evidence but fail the qualification step.

- [ ] **Step 4: Run focused tests and the full suite**

  Run:

  ```bash
  PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_ordered_history_separator -v
  PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v
  ```

  Expected: every test passes with pristine output.

- [ ] **Step 5: Run the local script only when an exact public environment is available**

  Run:

  ```bash
  PYTHONPATH=kaggle/src:experiments OUTDIR=evidence/arc3-public-g6-ordered-history-separator python experiments/arc3_public_g6_ordered_history_separator.py
  ```

  Expected: one declared scientific classification and a validating result
  artifact.  If the pinned environment is unavailable locally, record that the
  hosted workflow is the execution boundary; do not synthesize evidence.

- [ ] **Step 6: Commit**

  ```bash
  git add .github/workflows/arc3-public-g6-ordered-history-separator.yml kaggle/tests/test_g6_ordered_history_separator.py
  git commit -m "Add hosted G6 ordered-history qualification gate"
  ```

- [ ] **Step 7: Push the exact branch and inspect hosted evidence**

  Push `arc3-public-g6-ordered-history-separator-v1`, wait for the dedicated
  workflow, then record exact head, run, job, artifact, digest, classification,
  separator witness or bounded negative, and remaining residual.  Do not merge.

- [ ] **Step 8: Synchronize ROS after genuine hosted evidence**

  Update Research Checkpoints, Campaign Registry, and Cold-Start Runbook.
  Update Canonical Research State only if the live ARC frontier changes.  State
  exactly what was separated or rejected and retain `UNKNOWN(target.projection@1)`
  unless a later experiment closes it.
