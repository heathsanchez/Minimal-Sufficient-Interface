from __future__ import annotations

import json
import os
from pathlib import Path

from arc3_public_g4_scale_action_ordering import run_path


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-g4-column-ownership-semantics"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)
WORD = "LSDDSL"


def main():
    first = run_path(WORD)
    verification = [run_path(WORD), run_path(WORD)] if first["progressed"] else []
    promoted = first["progressed"] and all(row["progressed"] for row in verification)
    result = {
        "status": "PROMOTED" if promoted else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if promoted else "WARRANTED NEGATIVE",
        "hypothesis": (
            "scale-normalized docking produces three column-ownership relations in order "
            "dock-only, mover-dominant, interlocked, interlocked, mover-dominant, dock-only; "
            "map these to the visible small-origin, large, and translated selector poses"
        ),
        "normalized_mover_counts": [0, 4, 3, 3, 4, 0],
        "word": WORD,
        "first": first,
        "verification": verification,
        "independent_replay_count": len(verification),
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": "exact public tn36 G4; one visible column-ownership factorization",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G4_COLUMN_OWNERSHIP_SEMANTICS={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
