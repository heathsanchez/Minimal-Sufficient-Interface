"""Route experiments from the authoritative programme frontier.

This is intentionally small: it does not decide mathematics, only whether a
known experiment is applicable to the current residual. Non-applicable
workflows must skip cleanly rather than fail after their version space is gone.

Size-free work is deliberately stage-typed. A broad SIZE_FREE_RENEWAL route
reactivated already-exhausted historical probes, so the residual text now
selects one precise experiment family instead of a whole research era.

Routing precedence matters: a later-stage residual can legitimately mention
retained earlier structure (for example Bad-shadow inside simultaneous
renewal). Therefore specific current-stage signatures must be tested before
broader inherited-structure signatures.
"""
from __future__ import annotations
import argparse, json, os


def route(frontier: dict) -> str:
    promoted = {x.get("id") for x in frontier.get("promoted", []) if x.get("status") == "PROMOTE"}
    residual = frontier["live_residual"]
    residual_type = residual["type"]
    residual_text = residual["text"].lower()
    closed_kappas = {int(x["kappa"]) for x in frontier.get("promoted", []) if x.get("status") == "PROMOTE" and "kappa" in x}
    spectrum = {int(k) for k in frontier.get("curvature_spectrum", {})}

    if residual_type == "VERIFICATION" and closed_kappas != spectrum:
        return "CURVATURE"
    if residual_type == "VERIFICATION" and closed_kappas == spectrum and "affine_D_excluded" not in promoted:
        return "AFFINE_D"

    if residual_type in {"ATTACHMENT", "REFRAME"} and "full_D_phase_frontier_closed" in promoted:
        # Most specific active size-free stage first. Later residuals retain
        # vocabulary from earlier stages, so broad keyword checks must follow.
        if "simultaneous" in residual_text and "renewal" in residual_text:
            return "SIZE_FREE_SIMULTANEOUS_RENEWAL"
        if "finite-model/ground consequence projection" in residual_text or (
            "ground consequence" in residual_text and "bad-shadow" in residual_text
        ):
            return "SIZE_FREE_SHADOW_GROUND"
        if "bad shadow" in residual_text or "bad-shadow" in residual_text:
            return "SIZE_FREE_SHADOW_FIRST_ORDER"
        return "SIZE_FREE_UNROUTED"

    return "UNROUTED"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect")
    ap.add_argument("--github-output", action="store_true")
    args = ap.parse_args()
    f = json.load(open("program_frontier.json"))
    assert f.get("authoritative") is True
    r = route(f)
    print("FRONTIER_ROUTE=" + r)
    print("LIVE_RESIDUAL_TYPE=" + f["live_residual"]["type"])
    if args.github_output:
        path = os.environ.get("GITHUB_OUTPUT")
        if path:
            with open(path, "a") as h:
                h.write("route=" + r + "\n")
    if args.expect and r != args.expect:
        raise SystemExit(f"route mismatch: expected {args.expect}, got {r}")


if __name__ == "__main__":
    main()
