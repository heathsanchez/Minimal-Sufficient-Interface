# ARC3 G6 Event-Segmented Boolean Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify the five still-untested rowwise Boolean relations over the two control codewords in each of six independently observed G6 marker-delimited route intervals.

**Architecture:** A pure helper extracts six ordered route segments from legal singleton marker events and aligns them to target columns by marker position. A public-environment experiment applies exactly the five remaining observable Boolean truth signatures, uses terminal progress as oracle, and requires two independent exact replays before promotion. A schema validator and hosted workflow seal the scientific boundary.

**Tech Stack:** Python 3.12, `unittest`, exact public Duck ARC-3 environment, GitHub Actions.

**Spec:** Approved conversation design: six observed marker events segment the 12-step route; exhaust only signatures `000`, `100`, `101`, `110`, `111`; no model calls or source inspection; promotion requires progress plus two exact replays.

## Global Constraints

- Exact public game `tn36-ef4dde99` only.
- Legal visible observations/actions only; no game-source inspection.
- Zero model calls inside qualification.
- Preserve every tested candidate and its terminal result.
- Bound each candidate/replay to at most 50 G6 actions.
- A positive requires two independent exact replays with identical semantic identity.
- A complete failure is `WARRANTED_NEGATIVE` only for this five-relation, event-segmented family.

## Review Focus

- Missing, duplicate, non-singleton, or non-terminal marker events must fail closed before target writes.
- Segment arity other than exactly two controls must fail closed rather than silently pair by index.
- Repeated observations of one control label with different codewords must fail closed.
- Marker-spatial order must determine target-column order and be invariant to chronological reversal.
- A promoted candidate must have two identity-matched progressing replays; a negative must retain all five variants.

---

### Task 1: Pure event segmentation and Boolean family

**Files:**
- Create: `kaggle/tests/test_g6_event_boolean_composition.py`
- Create: `experiments/arc3_public_g6_event_boolean_composition.py`

**Interfaces:**
- Consumes: route string, `(step, marker_position)` events, per-control six-bit codes.
- Produces: `event_segments(route, events)`, `compose_bits(signature, left, right)`, and `spatial_columns(...)`.

- [ ] Write tests for exact six two-control segments, spatial reversal, all five truth signatures, malformed marker boundaries, and inconsistent code observations.
- [ ] Run `PYTHONPATH=kaggle/src:experiments python -m unittest kaggle.tests.test_g6_event_boolean_composition -v`; expect failure because the experiment module is absent.
- [ ] Implement only the pure functions and typed validation required by those tests.
- [ ] Rerun the focused tests; expect all pass.
- [ ] Commit the RED→GREEN unit.

### Task 2: Exact public qualification and evidence schema

**Files:**
- Modify: `experiments/arc3_public_g6_event_boolean_composition.py`
- Modify: `kaggle/tests/test_g6_event_boolean_composition.py`

**Interfaces:**
- Consumes: `enter_g6`, legal control clicks, marker observations, source codewords, target cells, submit control.
- Produces: `result.json` with status, classification, five variants, event trace, action counts, replay identity, and exact claim boundary.

- [ ] Add failing schema tests for zero model/source access, exact five-signature census, negative evidence completeness, 50-action bound, and two-replay promotion identity.
- [ ] Run the focused tests; expect the missing validator/executor behavior to fail.
- [ ] Implement the public run, candidate execution, promotion/negative classification, and validator.
- [ ] Rerun focused tests and then `PYTHONPATH=kaggle/src:experiments python -m unittest discover -s kaggle/tests -v`; expect all pass.
- [ ] Commit the RED→GREEN qualification unit.

### Task 3: Hosted exact-head gate

**Files:**
- Create: `.github/workflows/arc3-public-g6-event-boolean-composition.yml`

**Interfaces:**
- Consumes: exact branch head and public Duck environment.
- Produces: hosted result/log artifact with run, job, artifact, digest, and sealed exact-head evidence.

- [ ] Add a workflow-schema test requiring the branch trigger, exact public game, full tests, experiment run, seal, and artifact upload.
- [ ] Run the focused schema test; expect failure because the workflow is absent.
- [ ] Add the minimal workflow and exact-head seal.
- [ ] Run focused and full suites; expect all pass.
- [ ] Commit, review the whole branch, publish through the authenticated GitHub connector, and inspect the hosted artifact.
- [ ] Update Canonical Research State, Research Checkpoints, Campaign Registry, and Cold-Start Runbook with exact hosted evidence and the next smallest residual.
