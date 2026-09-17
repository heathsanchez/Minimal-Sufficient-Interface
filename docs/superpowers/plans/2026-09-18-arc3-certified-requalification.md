# MG-ARC5 Certified Requalification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded consequence-certified requalification so a retained ARC capability must match its witnessed effect prefix before continued cross-level reuse.

**Architecture:** `ConsequenceController` captures and evaluates effect checkpoints; `MemoryGraphController` schedules probe vs admitted transfer; `ArcMemoryGraph` persists source contracts, target trial status, matched checkpoint count, and cumulative target allowance. Existing affordance acquisition and exact refutation remain unchanged.

**Tech Stack:** Python 3.12, `unittest`, GitHub Actions, ARC SDK `arc-agi==0.9.9`, `arcengine==0.9.3`.

**Spec:** `docs/superpowers/specs/2026-09-18-arc3-certified-requalification-design.md`

## Global Constraints

- No game-specific solution constants or game-ID branches in production policy.
- Probe + admitted transfer share the existing target action allowance; no refunds across reset/restart/source alternatives.
- Source mismatch is not semantic refutation and must not delete the source capability.
- Legacy MG-ARC4 loads without fabricated certificates.
- Preserve exact replay, terminal refutation, affordance learning, standalone vendoring and offline notebook behavior.
- Public diagnostics remain development-set measurements, not hidden generalization claims.

---

### Task 1: Persistent capability contracts

**Files:**
- Modify: `kaggle/src/metalogic_arc3/memory_graph.py`
- Test: `kaggle/tests/test_requalification_contract.py`

**Interfaces:**
- Produces: `add_capability_contract(...)`, `capability_candidates(for_level)`, `transfer_trial(...)`, canonical MG-ARC5 serialization/parsing.

- [ ] **Step 1: Write failing memory tests**

Add tests that create a capability, attach two ordered checkpoints, serialize/restart, and verify exact canonical recovery. Add malformed-row tests for duplicate indices, checkpoint/action disagreement, invalid status, unsupported capability and aggregate target overspend. Add an MG-ARC4 migration test asserting no contract is fabricated.

- [ ] **Step 2: Run focused tests and verify RED**

Run:
```bash
python -m unittest kaggle.tests.test_requalification_contract -v
```
Expected: FAIL because MG-ARC5 contract APIs/statuses do not exist.

- [ ] **Step 3: Implement minimal MG-ARC5 persistence**

Add canonical contract records keyed by existing capability identity:
```python
(source_context, program, source_level, target_level)
```
with checkpoint rows:
```python
(index, action_key, descriptor, structural_signature)
```
and `protected_outcome='LEVEL_INCREMENT'` plus deterministic contract digest.

Target trial statuses must be exactly:
```python
OPEN_PROBE
PREFIX_REQUALIFIED
CONTRACT_MISMATCH
EXPIRED_UNCONFIRMED
WITNESSED_PROGRESS
```
Keep the existing aggregate target allowance accounting.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the focused test module and `kaggle/tests/test_memory_graph.py`.

- [ ] **Step 5: Commit persistent contract layer**

Commit message:
```text
feat: persist MG-ARC5 capability contracts
```

### Task 2: Source witness capture

**Files:**
- Modify: `kaggle/src/metalogic_arc3/consequence_controller.py`
- Test: `kaggle/tests/test_requalification_contract.py`

**Interfaces:**
- Produces: bounded episode checkpoint buffer; on observed level increment, attaches up to eight action/descriptor/effect checkpoints to the exact capability record installed by the base controller.

- [ ] **Step 1: Write failing source-capture tests**

Exercise `ConsequenceController` with controlled frames. Assert no contract exists before progress; after an observed level increment, assert the stored program and ordered checkpoints correspond to the actual actions/effects, and only the first eight are retained.

- [ ] **Step 2: Verify RED**

Run the focused test and confirm missing witness-capture behavior.

- [ ] **Step 3: Implement checkpoint capture**

Extend `_pending_effect` to retain action source and descriptor. In `_record_effect`, normalize `EffectSignature.structural()` (or equivalent tuple for dimension changes) and append `(action, descriptor, structural)` to a bounded episode witness. Override or extend the progress path so the just-installed capability receives that witness. Clear only transient episode witness on reset/progress; persistent `.mg` stays intact.

- [ ] **Step 4: Verify GREEN and old consequence tests**

Run:
```bash
python -m unittest kaggle.tests.test_requalification_contract kaggle.tests.test_consequence_affordance_controller kaggle.tests.test_affordance_deployment -v
```

- [ ] **Step 5: Commit witness capture**

Commit message:
```text
feat: capture source consequence certificates
```

### Task 3: Probe-gated transfer

**Files:**
- Modify: `kaggle/src/metalogic_arc3/memory_controller.py`
- Modify: `kaggle/src/metalogic_arc3/consequence_controller.py`
- Test: `kaggle/tests/test_requalification_contract.py`
- Test: `kaggle/tests/test_transfer_contract.py`

**Interfaces:**
- `MemoryGraphController` exposes current expected probe checkpoint and transitions transfer trial state.
- `ConsequenceController._record_effect` reports normalized probe results back to the transfer scheduler.

- [ ] **Step 1: Write failing probe tests**

Cover:
1. first checkpoint mismatch -> `CONTRACT_MISMATCH`, no further transfer, source capability retained;
2. matching all bounded checkpoints -> `PREFIX_REQUALIFIED` then continued `transfer` actions;
3. probe actions count against the same target allowance;
4. reset/restart cannot repeat a mismatched probe;
5. target progress during probe -> `WITNESSED_PROGRESS` and new capability contract;
6. exact trie closure still overrides a probe action.

- [ ] **Step 2: Verify RED**

Run focused tests and confirm current MG-ARC4 unconditional transfer fails the new expectations.

- [ ] **Step 3: Implement scheduler state**

At transfer start, select the freshest eligible **certified** capability. Label initial actions `transfer_probe`. Keep expected checkpoint index and matched count. Do not continue beyond the bounded probe unless the consequence layer confirms each checkpoint. On mismatch, persist target status and clear the active macro. On successful prefix, persist `PREFIX_REQUALIFIED` and continue within remaining allowance. Uncertified legacy capabilities remain stored but are not consequence-certified cross-level transfer candidates.

- [ ] **Step 4: Verify GREEN plus transfer regressions**

Run both requalification and MG-ARC4 transfer-contract test modules.

- [ ] **Step 5: Commit probe gate**

Commit message:
```text
feat: gate ARC transfer on consequence requalification
```

### Task 4: Generated-agent parity and full contracts

**Files:**
- Modify only if required: `kaggle/scripts/build_agent.py`
- Test: `kaggle/tests/test_affordance_deployment.py`
- Test: `kaggle/tests/test_requalification_contract.py`

**Interfaces:** generated `kaggle/agent/my_agent.py` must preserve MG-ARC5 behavior exactly.

- [ ] **Step 1: Add generated parity test**

Run the same matching/mismatching probe sequence through modular and generated controllers and compare chosen action/source plus canonical memory state.

- [ ] **Step 2: Verify RED if vendoring/parity is incomplete**

- [ ] **Step 3: Make minimal build changes if required**

No new runtime dependencies.

- [ ] **Step 4: Run all unit tests and compile/build artifacts**

```bash
python -m unittest discover -s kaggle/tests -p 'test_*.py' -v
python kaggle/scripts/build_agent.py
python -m py_compile kaggle/agent/my_agent.py
python kaggle/scripts/build_notebook.py
```

- [ ] **Step 5: Commit deployment parity**

Commit message:
```text
ci: qualify MG-ARC5 generated requalification
```

### Task 5: Matched development qualification

**Files:**
- Create: `.github/workflows/arc3-certified-requalification.yml`
- Create: `kaggle/scripts/requalification_audit.py`
- Create after measurement: `kaggle/reports/2026-09-18-certified-requalification.md`

**Interfaces:** paired candidate / MG-ARC4 prior / no-transfer / no-affordance measurements over the same pinned worlds.

- [ ] **Step 1: Add source-blind matched evaluator wrapper**

Reuse `benchmark_audit.py`. Record per trial:
```text
levels, milestones, action count, source_counts,
probe actions, admitted transfer actions,
contract statuses, matched checkpoint counts,
capability records, memory format/digest
```

- [ ] **Step 2: Run CI qualification**

Required gates:
- all unit tests green;
- standalone agent + offline notebook build;
- `bt11` candidate remains 5-level WIN in <=73 interactions;
- `vc33` candidate remains >=2 levels within 400;
- paired starts/manifests/budgets match;
- no ERROR/TIMEOUT cells.

The 109 -> 93 gap is a measurement target, not a hard code-correctness gate.

- [ ] **Step 3: Inspect full logs and artifact**

Do not infer results from workflow status alone. Read exact milestones and source counts.

- [ ] **Step 4: Write measured report**

Distinguish mechanism correctness, bounded public development evidence, fixture control, and unmeasured hidden-game generalization.

- [ ] **Step 5: Final verification**

Re-fetch branch head, completed workflow, job steps/logs and artifact digest before making completion claims.