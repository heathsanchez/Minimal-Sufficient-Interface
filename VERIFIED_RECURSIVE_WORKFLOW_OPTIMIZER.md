# Verified Recursive Workflow Optimizer

## Frozen baseline

`Pi0_value_per_cost` is the smallest executable incumbent: it ranks licensed
proposals by declared target-relevant value per cost. `Pi1_directness_gate`
adds one change only: lexicographic `PUSH > PROBE > REFRAME > META` before the
same within-class ranking.

The controller persists the requested problem contract, terminal state,
successes, failures, open residuals, developmental graph slots, and hashed
event provenance. Domain truth is supplied by an external verifier callback;
the controller cannot mark its own proposal correct.

## Experiment 1: directness baseline

`directness_baseline_experiment.py` is a matched, deterministic four-case
replay. All cases have a viable direct route whose cost exactly fills the
budget, plus a cheaper higher-ratio side action. Two cases are development;
two use disjoint held-out identifiers and unseen side-action classes.

The experiment tests only whether the gate enforces its stated anti-wandering
doctrine under that condition. It does not establish general solver
improvement: the cases intentionally instantiate the condition the doctrine
was designed for. Consequently this result may qualify the gate for the next
external A/B experiment, but must not be reported as the programme milestone
`Pi1 > Pi0 on held-out problems` without that scope qualifier.

Run:

```text
python -m unittest tests.test_workflow_optimizer -v
python directness_baseline_experiment.py
```

The exact frozen case table and raw results are written to
`artifacts/directness_baseline_v1.json` with a SHA-256 digest of the cases.

## Licensed next experiment

The resulting residual is external validity, not controller correctness. The
next experiment must use pre-existing tasks with objective verifiers and
matched budgets, and must include cases where PUSH is viable as well as cases
where it is exhausted. This discriminates a useful directness gate from a
policy that merely delays necessary probing or reframing.
