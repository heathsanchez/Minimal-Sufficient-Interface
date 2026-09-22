from __future__ import annotations

import json
import os
import re
import statistics
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODEL = os.environ.get("JOIN_MODEL", "Qwen/Qwen3.6-27B")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass(frozen=True)
class Choice:
    side: str
    color: int
    mask: str
    area: int


@dataclass(frozen=True)
class Episode:
    name: str
    good: Choice
    bad: Choice


# These micro-fixtures deliberately preserve the public bt33 target geometry
# while perturbing incidental coordinates. They are a separator test for JOIN,
# not a benchmark score claim.
TRAIN = (
    Episode(
        "public-shape-original-colors",
        Choice(side="left", color=14, mask="11/10", area=3),
        Choice(side="right", color=8, mask="11/01", area=3),
    ),
    Episode(
        "prospective-color-boundary",
        Choice(side="left", color=8, mask="11/10", area=3),
        Choice(side="right", color=14, mask="11/01", area=3),
    ),
)

HELD_OUT = (
    Episode(
        "heldout-mirror-original-colors",
        Choice(side="right", color=14, mask="11/10", area=3),
        Choice(side="left", color=8, mask="11/01", area=3),
    ),
    Episode(
        "heldout-mirror-swapped-colors",
        Choice(side="right", color=8, mask="11/10", area=3),
        Choice(side="left", color=14, mask="11/01", area=3),
    ),
)


def as_record(ep: Episode) -> dict[str, Any]:
    return {
        "episode": ep.name,
        "success": ep.good.__dict__,
        "failure": ep.bad.__dict__,
    }


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError(f"model returned no JSON object: {text[:500]!r}")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("JOIN response is not an object")
    return value


def call_join(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is required")
    system = """You are the JOIN operator in an evidence-governed developmental controller.
Your job is NOT to solve one episode. Search for the same causal role under different surfaces.
Propose the smallest transferable law that explains BOTH successes and failures.
Incidental coordinates may change on held-out cases.

Return JSON only with exactly:
{
  "feature": one of ["side","color","mask","area"],
  "value": JSON scalar,
  "shared_structure": short string,
  "important_difference": short string,
  "predicted_transport": short string,
  "cheapest_falsifier": short string
}

The law is only a candidate. External held-out evidence decides whether it is retained."""
    user = (
        "Observed episodes (held-out cases are NOT shown):\n"
        + json.dumps(evidence, indent=2, sort_keys=True)
        + "\nChoose one feature/value rule that identifies the successful choice "
          "and rejects the failed choice across the evidence. Prefer a causal/structural "
          "invariant over an incidental coordinate when both fit."
    )
    body = json.dumps(
        {
            "model": MODEL,
            "temperature": 0,
            "top_p": 1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode())
    text = payload["choices"][0]["message"]["content"]
    out = parse_json_object(text)
    out["_usage"] = payload.get("usage") or {}
    return out


def value(choice: Choice, feature: str) -> Any:
    if feature not in {"side", "color", "mask", "area"}:
        raise ValueError(f"unsupported JOIN feature: {feature}")
    return getattr(choice, feature)


def law_selects(ep: Episode, feature: str, expected: Any) -> bool:
    good = value(ep.good, feature) == expected
    bad = value(ep.bad, feature) == expected
    return bool(good and not bad)


def normalize_expected(feature: str, raw: Any) -> Any:
    if feature in {"color", "area"}:
        return int(raw)
    return str(raw)


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    feature = str(candidate.get("feature", "")).strip()
    expected = normalize_expected(feature, candidate.get("value"))
    train = [law_selects(ep, feature, expected) for ep in TRAIN]
    held = [law_selects(ep, feature, expected) for ep in HELD_OUT]
    return {
        "feature": feature,
        "value": expected,
        "train_pass": all(train),
        "heldout_pass": all(held),
        "train_cases": train,
        "heldout_cases": held,
        "falsifier_supplied": bool(str(candidate.get("cheapest_falsifier", "")).strip()),
    }


def baseline() -> dict[str, Any]:
    # Current autonomous Flash's first mouse probe is spatial: leftmost component.
    feature, expected = "side", "left"
    return {
        "feature": feature,
        "value": expected,
        "train_pass": all(law_selects(ep, feature, expected) for ep in TRAIN),
        "heldout_pass": all(law_selects(ep, feature, expected) for ep in HELD_OUT),
        "heldout_cases": [law_selects(ep, feature, expected) for ep in HELD_OUT],
    }


def main() -> None:
    evidence = [as_record(ep) for ep in TRAIN]
    trials = []
    for i in range(3):
        candidate = call_join(evidence)
        verdict = evaluate(candidate)
        trials.append({"trial": i + 1, "candidate": candidate, "verdict": verdict})
        print(json.dumps(trials[-1], indent=2))

    passing = [
        row
        for row in trials
        if row["verdict"]["train_pass"]
        and row["verdict"]["heldout_pass"]
        and row["verdict"]["falsifier_supplied"]
    ]
    base = baseline()
    adds_unique_value = bool(
        len(passing) >= 2
        and base["train_pass"]
        and not base["heldout_pass"]
    )
    features = [row["verdict"]["feature"] for row in passing]
    result = {
        "protocol": "JOIN semantic search admission separator v0",
        "model": MODEL,
        "evidence_label": "PROSPECTIVE_FROZEN",
        "train": evidence,
        "held_out_names": [ep.name for ep in HELD_OUT],
        "baseline": base,
        "join_trials": trials,
        "passing_join_trials": len(passing),
        "passing_features": features,
        "modal_passing_feature": statistics.mode(features) if features else None,
        "join_adds_unique_value": adds_unique_value,
        "decision": "ADMIT_JOIN_HOOK" if adds_unique_value else "REJECT_JOIN_HOOK",
        "scope": (
            "episodic semantic synthesis only; no authoritative state; "
            "candidate laws require external held-out qualification"
        ),
    }
    Path("join-semantic-search-result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print("JOIN_ADDS_UNIQUE_VALUE=" + ("PASS" if adds_unique_value else "FAIL"))


if __name__ == "__main__":
    main()
