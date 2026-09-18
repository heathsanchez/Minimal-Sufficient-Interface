"""Aggregate the exact ft09 fatal-chain campaign into one negative certificate.

Inputs are pinned workflow artifacts from:
- the original (54,54) progression extension, and
- five disjoint one-deviation bands covering offsets 0, 6, 12, 18, 24.

The certificate mechanically checks:
1. the original retained fatal chains all end in GAME_OVER with no protected progress;
2. the union of tested source digests equals the union of every nonterminal source
   digest on those fatal chains;
3. every counterfactual probe has no protected progress;
4. all probe outcomes are GAME_OVER or immediate no-change;
5. the five bands are non-overlapping by source digest;
6. the total tested alternative count matches the source count times six.

This is a bounded exact hazard certificate over the declared three retained
(54,54) progression chains and the six tested primary alternatives per source.
It is not a universal theorem about all ft09 states or all interventions.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ft09-fatal-basin-certificate-results"

PROGRESSION = OUT / "progression.json"
BANDS = [
    (0, OUT / "band-0.json"),
    (6, OUT / "band-6.json"),
    (12, OUT / "band-12.json"),
    (18, OUT / "band-18.json"),
    (24, OUT / "band-24.json"),
]
ALTERNATIVES_PER_STATE = 6


def read(path: Path):
    return json.loads(path.read_text())


def fatal_chain_sources(progression: dict) -> set[str]:
    if progression["result"]["status"] != "NO_PROTECTED_PROGRESS":
        raise AssertionError("progression premise changed")
    rows = progression["endpoint_results"]
    if len(rows) != 3:
        raise AssertionError("expected exactly three retained fatal chains")

    sources = set()
    for chain in rows:
        if chain["stop_reason"] != "GAME_OVER":
            raise AssertionError("retained progression no longer ends in GAME_OVER")
        if chain.get("progress") is not None:
            raise AssertionError("retained progression unexpectedly has protected progress")
        extension = chain["extension"]
        if not extension or extension[-1]["state"] != "GAME_OVER":
            raise AssertionError("fatal chain terminal row changed")
        for row in extension:
            sources.add(str(row["source"]))
    return sources


def main():
    progression = read(PROGRESSION)
    expected_sources = fatal_chain_sources(progression)

    tested_sources: set[str] = set()
    band_sources: list[set[str]] = []
    probe_rows = []
    band_summaries = []

    for expected_offset, path in BANDS:
        data = read(path)
        if data["result"]["status"] != "NO_PROTECTED_PROGRESS":
            raise AssertionError(f"band {expected_offset} unexpectedly found progress")

        actual_offset = int(data.get("tail_offset", 0))
        if actual_offset != expected_offset:
            raise AssertionError(
                f"band offset mismatch: expected {expected_offset}, got {actual_offset}"
            )

        probes = list(data["probes"])
        sources = {str(row["source"]) for row in probes}
        source_count = int(data["source_state_count"])
        if len(sources) != source_count:
            raise AssertionError(
                f"band {expected_offset} source count mismatch: "
                f"{len(sources)} != {source_count}"
            )

        for prior in band_sources:
            overlap = sources & prior
            if overlap:
                raise AssertionError(
                    f"band {expected_offset} overlaps prior source set: {sorted(overlap)[:3]}"
                )
        band_sources.append(sources)

        expected_probes = source_count * ALTERNATIVES_PER_STATE
        if len(probes) != expected_probes:
            raise AssertionError(
                f"band {expected_offset} probe count mismatch: "
                f"{len(probes)} != {expected_probes}"
            )

        statuses = Counter()
        for row in probes:
            if row.get("progress") is not None:
                raise AssertionError("counterfactual probe unexpectedly has protected progress")
            status = str(row["status"])
            statuses[status] += 1
            if status not in ("GAME_OVER", "ESCAPE_NO_CHANGE"):
                raise AssertionError(
                    f"unexpected bounded hazard probe outcome {status}"
                )

        tested_sources.update(sources)
        probe_rows.extend(probes)
        band_summaries.append(
            {
                "offset": expected_offset,
                "source_states": source_count,
                "probes": len(probes),
                "status_counts": dict(statuses),
            }
        )

    if tested_sources != expected_sources:
        missing = sorted(expected_sources - tested_sources)
        extra = sorted(tested_sources - expected_sources)
        raise AssertionError(
            "fatal source coverage mismatch: "
            f"missing={missing[:5]} extra={extra[:5]}"
        )

    status_counts = Counter(str(row["status"]) for row in probe_rows)
    report = {
        "status": "CLOSED_BOUNDED_FATAL_BASIN_CERTIFICATE",
        "interpretation": (
            "all retained nonterminal states on the three exact ft09 (54,54) "
            "fatal progression chains were covered by six ranked one-deviation "
            "counterfactuals each; none produced protected progress"
        ),
        "claim_boundary": (
            "bounded to the three retained progression chains and the six tested "
            "primary alternatives per source; this is not a universal ft09 hazard theorem"
        ),
        "source_chain_count": len(progression["endpoint_results"]),
        "fatal_source_states": len(expected_sources),
        "tested_source_states": len(tested_sources),
        "alternatives_per_source": ALTERNATIVES_PER_STATE,
        "probe_count": len(probe_rows),
        "status_counts": dict(status_counts),
        "bands": band_summaries,
        "coverage": {
            "source_sets_equal": tested_sources == expected_sources,
            "untested_fatal_sources": 0,
            "extra_tested_sources": 0,
        },
        "negative_capability": {
            "family": "ft09_retained_5454_fatal_basin",
            "protected_progress_observed": False,
            "safe_compilation_use": (
                "do not reward or reacquire this retained progression family "
                "as a generic high-value state-changing capability"
            ),
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ft09-fatal-basin-certificate.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    )
    print(
        "FT09_FATAL_BASIN_CERTIFICATE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_FT09_FATAL_BASIN_CERTIFICATE=PASS", flush=True)


if __name__ == "__main__":
    main()
