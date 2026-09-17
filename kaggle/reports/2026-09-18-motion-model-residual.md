# MG-ARC7 action-conditioned motion model — qualified residual

Date: 18 September 2026 NZ time

## Verdict

MG-ARC7 is not promoted over MG-ARC5 yet. It successfully learns generic action-conditioned component transport and materially changes ls20 exploration, but does not complete a level within the 400-interaction development budget.

## Evidence

- Branch: `arc3-motion-model-v1`
- Tested head: `6d8737cef3d7bc5db003a77b4f56e92082ed7ca4`
- Source implementation before audit-only commits: `7a07418512e536301f0470562f67b8fc28dcfe94`
- Prior champion: `07fe94a80edfbb295049d4140aef14ef2b47524b`
- Run: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35284520918
- Job: https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/35284520918/job/105413781659
- Candidate generated-agent SHA256: `92846a124d4f02b4bdde11fd0ec8bd74a3f8f9eb495b49c2ae1a8bbb696d1428`
- 85/85 tests passed; standalone agent and notebook built; all 12 matched cells completed.

## Results

| World | MG-ARC7 | MG-ARC5 prior | no_motion |
|---|---:|---:|---:|
| bt11 fixture | 5/5 WIN @73 | 5/5 WIN @73 | 5/5 WIN @73 |
| ft09 public | 0/400 | 0/400 | 0/400 |
| ls20 public | 0/400 | 0/400 | 0/400 |
| vc33 public | L1@64, L2@93 | L1@64, L2@93 | L1@64, L2@93 |

On ls20 the candidate learned 3 transport component classes, 9 action/component vector rows, and 8 reliable motion controls. It used `motion_frontier` 232 times. This causally changed the trajectory: distinct observations fell 355→324 and affordance-selected actions fell 259→28.

The important negative signal is that zero-observation-change steps rose 9→51. The learned global action→motion relations are real enough to drive behavior, but the frontier selector assumes a modeled move remains available at every position. Obstacles/boundaries therefore leave a predicted frontier “unvisited,” causing repeated attempts at a locally blocked edge.

## Next obligation

The next repair is position-scoped obstruction memory:

[
(	ext{component class},	ext{position},	ext{action})
	o
{	ext{transport observed},	ext{blocked/other}}.
]

A blocked move does **not** refute the global action→motion capability. It only revokes that proposal at the current local state and forces an alternate route. This is the same certified-replacement discipline at a smaller scope: preserve the global capability, narrow its applicability contract.

No Kaggle submission, merge, or official PR was made.
