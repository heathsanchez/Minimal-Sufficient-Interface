# TaskSAT rate-timeline interval contract audit

## Objective

Resolve the smallest observable consequence of a second TaskSAT semantic fork found while reconciling the CAD audit.

Pinned target: `nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0`.

## Conflicting source meanings

The public manual gives this concrete rate-timeline example:

```tasknet
battery : rate [-5.0, 5.0] bounds [0.0, 100.0] = 50.0 initial_rate = -0.1;
```

and immediately describes:

- `[-5,5]` as **Rate bounds**;
- `[0,100]` as **Value bounds**, with value clamped to them.

The readable grammar likewise renders a rate timeline as

```text
rate [<min_rate>, <max_rate>] bounds [<min>, <max>] = <initial> initial_rate = <rate>
```.

But the current Python AST calls the first interval `range`, and the SMT encoder applies every numeric timeline's `range` to its **value variables** at all zone boundaries. Its separate rate variables are initialized by `initial_rate`, but this first interval is not applied to them.

The executable Lean validator also checks its first `range` against the value state; its older rate representation does not carry the Python encoder's separate rate variable / `initial_rate` state, so it is not an independent current rate-semantics authority.

## Cheapest decisive experiment

Run the manual example itself through the pinned Python/Z3 encoder with one inert task.

Then change only the first interval:

```text
manual:  rate [-5,5]   bounds [0,100] = 50 initial_rate=-0.1
control: rate [0,100]  bounds [0,100] = 50 initial_rate=-0.1
```

If the manual interpretation were implemented, the first is internally consistent: value 50 lies in value bounds and rate -0.1 lies in rate bounds.

If the current Python interpretation is implemented, the first is unsatisfiable immediately because the VALUE is simultaneously fixed to 50 and constrained to lie in [-5,5]. The control removes exactly that conflict.

## Promotion boundary

**WARRANTED** only if the pinned CI run shows:

- both source texts pass TaskSAT well-formedness;
- manual example: UNSAT;
- one-interval control: SAT.

That establishes a documentation/implementation semantic divergence. It does **not** decide which interpretation matches MEXEC.

## Relation to the CAD work

This is the same pattern at a different interface:

[
	ext{surface DSL meaning}
;
otleftrightarrow;
	ext{encoder state meaning}.
]

The CAD branch handles the exact real-algebraic disagreement region once the source contract is fixed. This branch tests whether the symbols feeding that algebraic layer have a stable meaning in the first place.

## Causal lineage

The divergence localizes to upstream commit
`094f61abe00835927278d90c0020654a8dc44da2` ("made major changes to atomic
timelines and rate timelines", 2026-03-31).

That single commit did all of the following:

- introduced separate RATE variables in the SMT encoder;
- added `initial_rate`;
- kept the first `RateTimeline.range` attached to the VALUE variables and to
  `_encode_timeline_ranges`;
- added manual prose saying that each numeric timeline's first interval is a
  range that a valid schedule must stay within and that this range is a subtype
  of `bounds`;
- then, in the very next documentation block, introduced the concrete example
  `rate [-5,5] bounds [0,100] = 50 initial_rate=-0.1` and labelled `[-5,5]`
  as **Rate bounds**.

So this is not a later documentation drift between unrelated revisions. The
contradictory meanings were introduced together in the same semantic redesign.

This explains why the issue can remain hidden: most committed fixtures use a
first interval that also contains the initial VALUE (often equal to
`bounds`), so the two readings are observationally identical there. The
manual's own `[-5,5]` / initial VALUE `50` example is the smallest
separator.

