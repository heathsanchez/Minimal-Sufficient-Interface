# TaskSAT × PVS CAD closeout evidence

## Sealed result

**WARRANTED**

The final consolidated qualification is GitHub Actions run
[36631502126](https://github.com/heathsanchez/Minimal-Sufficient-Interface/actions/runs/36631502126),
job `109621591975`, against closeout commit
`16b23ddb910e4660059e7ba25a2ddef89a0371f3`.

The run completed **SUCCESS** and sealed artifact:

- name: `tasksat-pvs-cad-closeout`
- artifact id: `11062851121`
- SHA-256: `c6bfbb14194d76dee3259f4fabcfdbbba695abb7b8e2b988f5077ad360f85514`
- CAD QED count: **10/10**

Pinned external boundary:

- TaskSAT: `f9d6063b45967a3fea578c47f54806aadaafe1b0`
- pvs_cad: `8750362e99c2ba0e9a0307dcaa39b9766c562feb`
- NASALib: `e426f69dc2680ad575491f93c5a51739ec8b25fa`
- PVS: `8.1.2`
- PVS Linux x86_64 bundle SHA-256:
  `5b7d859feff90fc7e566c669a36aaea0254e762c7a723260cf5fd7e1721fcf1b`

## Green executable gates

The same run independently reproduced all of the following before the CAD
proof stage:

1. Python well-formedness accepts both `R subset B` and `B subset R`:
   **WARRANTED_MISSING_CONTAINMENT_CHECK**.
2. The manual's documented rate example is well-formed but **UNSAT** under
   the Python/Z3 encoder, while the one-interval control is **SAT**:
   **WARRANTED_RATE_INTERVAL_DOCUMENTATION_IMPLEMENTATION_DIVERGENCE**.
3. Contract-compliant assignment witness
   `R=[10,100], B=[0,100], a=110` is **UNSAT** before re-clamping.
4. The same witness is **SAT** after the disposable re-clamp repair.
5. TaskSAT's original numeric-assignment regression remains green:
   **1 passed**.

## Verified CAD obligations

The final manifest contains ten QED lines:

- `assignment_output_agreement_exact`
- `r_subset_b_lower_touch_has_validity_divergence`
- `r_subset_b_upper_touch_has_validity_divergence`
- `b_subset_r_always_has_validity_divergence`
- `reclamp_preserves_bounds`
- `contract_compliant_witness_has_validity_divergence`
- `historical_witness_is_b_subset_r`
- `strict_interior_reference_valid_implies_python_valid`
- `strict_interior_python_valid_implies_reference_valid`
- `r_subset_b_cases_exhaustive`

Together these establish the exact current/public-contract result:

[
oxed{
exists a:;
[operatorname{clamp}_B(a)in R]
e[ain R]
iff
R	ext{ touches at least one endpoint of }B
}
]

for `R subset B`, with the normalized form
`B=[0,W]`, `R=[p,W-q]`:

[
oxed{p=0 lor q=0.}
]

## Preserved negative result

The earlier five-variable strict-interior clamp-graph presentation remained
OPEN / timed out. It is preserved as a verifier-performance negative result.
Eliminating the auxiliary clamp-output variable and splitting the statement
into two four-variable implications produced **2/2 QED**, so the mathematical
residual is closed.

## Qualification note

During the consolidated run, one optional preflight pvs-cli typecheck command
printed a relative-path “file not found” message. It was not a gate and did
not terminate the step. The actual `cliprove.sh` proof subsequently loaded
the same closeout theory and produced
`r_subset_b_cases_exhaustive QED`; the sealed manifest counts that proof.
No warranted claim depends on the failed preflight lookup.
