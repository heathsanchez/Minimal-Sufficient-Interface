"""Route experiments from the authoritative programme frontier.

This is intentionally small: it does not decide mathematics, only whether a
known experiment is applicable to the current residual. Non-applicable
workflows must skip cleanly rather than fail after their version space is gone.
"""
from __future__ import annotations
import argparse, json, os


def route(frontier: dict) -> str:
    promoted = {x.get("id") for x in frontier.get("promoted", []) if x.get("status") == "PROMOTE"}
    residual_type = frontier["live_residual"]["type"]
    closed_kappas = {int(x["kappa"]) for x in frontier.get("promoted", []) if x.get("status") == "PROMOTE" and "kappa" in x}
    spectrum = {int(k) for k in frontier.get("curvature_spectrum", {})}

    if residual_type == "VERIFICATION" and closed_kappas != spectrum:
        return "CURVATURE"
    if residual_type == "VERIFICATION" and closed_kappas == spectrum and "affine_D_excluded" not in promoted:
        return "AFFINE_D"
    if residual_type in {"ATTACHMENT", "REFRAME"} and "full_D_phase_frontier_closed" in promoted:
        return "SIZE_FREE_RENEWAL"
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
