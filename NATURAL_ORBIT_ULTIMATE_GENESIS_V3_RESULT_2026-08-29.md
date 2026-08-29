# Natural Orbit Ultimate Genesis V3 — 2026-08-29

## Classification

`NATURAL_RAW_POSITION_REPRESENTATION_GENESIS_BOUNDED_POSITIVE`

Deciding workflow:

- Run: `33230106920`
- Job: `99041307770`
- Head SHA: `d277a20fc36e2ce4c86d01d22432b2ec72037c58`
- Workflow: `natural orbit ultimate genesis v3 mdl`
- Conclusion: **success**

## Question

Can a bounded developmental learner start from raw position histories, without being supplied velocity, acceleration, force, orbit, derivative, an integrator, an inverse-square family, or a radial-power family, and synthesize an executable recurrence that transfers to a sealed natural regime?

## Frozen information boundary

The learner receives anonymous two-step position history `(x_t, x_{t-1})` from JPL Horizons trajectories for Earth, Venus, and Mercury during discovery.

It is supplied only a generic typed Euclidean expression substrate:

- current vector `x`
- previous vector `p`
- scalar constant `1`
- `norm`
- `dot`
- scalar arithmetic
- reciprocal
- vector addition/subtraction
- scalar-vector scaling
- bounded expression cost
- bounded residual-guided sparse assembly

It is **not** supplied:

- velocity
- acceleration
- derivatives or finite differences as targets
- force
- orbit
- Verlet or another named integrator
- inverse-square law
- `x / ||x||^3` as a primitive
- a radial power-law family or exponent search

Mars is sealed until the recurrence is frozen.

## Developmental rule

Each generation:

1. compositionally generates candidate structural features from the generic typed alphabet;
2. fits a new feature only to the residual of the retained recurrence;
3. retains already promoted structure;
4. allows a generic minimum-description-length realization of a coefficient when a fitted value is already within 1% of a small rational (numerators `-12..12`, denominators `1..4`);
5. selects by worst protected multi-step future consequence over the unsealed discovery regimes;
6. promotes only a consequence-improving extension.

The MDL rule is generic and not physics-specific, but it remains part of the supplied developmental protocol and therefore part of the boundedness of the result.

## Generated recurrence

The successful run generated, in order:

1. `(p-(x+x))` with coefficient exactly `-1` after generic MDL realization. This is behaviorally `2 x_t - x_{t-1}`.
2. `scale(inv(((norm(x)*norm(x))*norm(x))),x)` with fitted coefficient `-0.0002957302411987253`. This is behaviorally `x_t / ||x_t||^3`.
3. `(scale(dot(x,p),p)-(x+x))` with coefficient `2.6070263438176926e-07`.
4. `scale(inv((dot(x,p)*dot(x,p))),p)` with coefficient `1.916677247291742e-08`.

The latter two are tiny residual refinements. A post-hoc behavioral reduction of the complete generated recurrence onto the three-term family

`a*x + b*p + c*x/||x||^3`

gives:

- `a = 1.9999989717884101`
- `b = -0.9999993188589655`
- `c = -0.0002956851995100518`
- relative behavioral residual `8.69897365691e-08`

Thus, on the tested discovery states, the learned executable recurrence is behaviorally almost exactly

`x_{t+1} = 2 x_t - x_{t-1} - mu x_t/||x_t||^3`

with `mu ≈ 0.0002957`, despite no derivative or force representation being supplied to the learner.

The post-hoc reduction is an interpretation check only; it was not used to select the recurrence.

## Held-out consequence

Relative RMSE versus the cold constant-velocity baseline:

| regime | warm / cold RMSE |
|---|---:|
| Earth | `0.00151214711232` |
| Venus | `0.000175742684726` |
| Mercury | `0.00146902766546` |
| Mars, sealed transfer | `0.00379051400326` |

The sealed Mars recurrence therefore has about `1 / 0.003790514 ≈ 264x` lower RMSE than the cold baseline, without Mars participating in discovery or parameter selection.

## Presentation invariance

The complete discovery procedure was rerun after a fixed orthogonal coordinate transformation. It selected the same structural recurrence and coefficients to numerical precision and reproduced the same held-out ratios, including sealed Mars transfer.

## Gates

All passed:

- `STRUCTURE_RETENTION=PASS`
- `GENERIC_MDL_REALIZATION=PASS`
- `RESIDUAL_ONLY_REFINEMENT=PASS`
- `NO_DERIVATIVE_TARGET=PASS`
- `NO_VELOCITY_ACCELERATION_FORCE_ONTOLOGY=PASS`
- `RAW_POSITION_REPRESENTATION_GENESIS=PASS`
- `DIRECT_EXECUTABLE_RECURRENCE_SYNTHESIS=PASS`
- `MULTI_REGIME_SEPARATOR=PASS`
- `SEALED_MARS_TRANSFER=PASS`
- `PRESENTATION_INVARIANCE_BEHAVIOURAL=PASS`
- `EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS`
- `NATURAL_ORBIT_ULTIMATE_GENESIS_V3=PASS`

## What the result supports

Under this frozen bounded protocol, raw natural position histories were sufficient for a generic compositional learner to generate an executable recurrence that is behaviorally almost exactly an inertial two-step update plus an inverse-cubic radial vector correction, without being given the derivative/force representation in which that physical law is normally stated. The generated recurrence transferred unchanged to sealed Mars and was invariant under an orthogonal change of coordinates.

The result is stronger than selecting an exponent within a supplied law family and stronger than synthesizing a force law after acceleration has already been chosen as the target representation.

## What it does not establish

It does **not** establish unrestricted autonomous physics discovery.

Still supplied are:

- Euclidean vector/scalar types;
- `norm`, `dot`, reciprocal and arithmetic primitives;
- history length two;
- a linear sparse assembly mechanism;
- expression-cost and search budgets;
- a generic MDL coefficient-compression rule;
- the choice of multiple planetary ephemeris regimes as discovery sources;
- JPL Horizons ephemerides rather than raw telescope measurements.

The planetary family also shares substantial pre-existing structure, so this is not evidence that arbitrary unrelated natural systems will induce the same representation.

## Scientific clue

The failed intermediate protocols were diagnostic:

- a single regime admitted spurious relations;
- insufficient expression depth blocked the transferable structure;
- global coefficient refitting let later residuals corrupt earlier structure;
- freezing raw fitted coefficients retained accidental bias rather than the structural relation.

The successful protocol instead retained **structure**, compressed an almost-exact structural coefficient to its simplest invariant realization, and made each later generation explain only the residual.

The emerging candidate developmental law is therefore more specific than generic search:

> discover a consequence-preserving structure; retain its simplest justified realization; expose the residual; add only the minimum new structure that changes protected future consequence; repeat.

That law remains a scientific hypothesis outside the bounded settings tested here.
