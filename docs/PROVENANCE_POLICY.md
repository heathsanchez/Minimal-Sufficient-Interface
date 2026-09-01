# Result provenance policy

Paper-facing experimental claims are bound to an exact provenance tuple

`(commit SHA, GitHub Actions workflow run ID, job/check conclusion)`.

A result is not reported as established until the workflow run for that exact commit has completed with `SUCCESS` for the load-bearing job/check. Success from an ancestor, sibling, pre-tightening, or otherwise different SHA is not transferred to the current claim. Queued, in-progress, cancelled, timed-out, infrastructure-failed, and ambiguous runs are reported with those statuses rather than promoted to scientific success.

When a certification rule, test, verifier, or experiment is tightened, the tightened commit requires a new exact-head run before the stronger claim is made.

This policy separates repository state, workflow execution, and scientific conclusion: an outer workflow status is evidence only for the exact code and internal checks that ran at the bound SHA.
