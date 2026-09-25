from __future__ import annotations

import json
import os
from pathlib import Path

from arc3_public_g4_four_control_docking import run_path


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-g4-shrink-direction"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

PATHS = (
    "ILDDDD", "IDLDDD", "IDDLDD", "LIDDDD",
    "DILDDD", "DIDLDD", "LDIDDD", "DLIDDD",
)


def main():
    variants = []
    selected = None
    verification = []
    for path in PATHS:
        row = run_path(path)
        variants.append(row)
        if row["progressed"]:
            checks = [run_path(path), run_path(path)]
            if all(check["progressed"] for check in checks):
                selected = path
                verification = checks
                break
    result = {
        "status": "PROMOTED" if selected else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if selected else "WARRANTED NEGATIVE",
        "hypothesis": (
            "the singleton selector is the shrink-to-small-pose action because its preview "
            "shares the large selector's anchor at the smaller transported scale"
        ),
        "paths": list(PATHS),
        "variants": variants,
        "selected": selected,
        "verification": verification,
        "independent_replay_count": len(verification),
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G4; all and only collision-free one-shrink/four-down/one-left "
            "routes with scale direction identified from equal-anchor previews"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G4_SHRINK_DIRECTION={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
