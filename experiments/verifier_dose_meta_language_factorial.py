#!/usr/bin/env python3
"""Frozen-design harness for the verifier-dose x meta-language experiment.

STATUS: protocol/harness, not a positive result.

Design: 5 verifier channels x 2 source-distinct meta-languages.  The channels include
repair-relevant residual information, an entropy/marginal-matched scrubbed intervention,
and a permuted/misleading intervention.  The harness makes channel visibility explicit
and rejects side-channel leakage through candidate ordering, stopping behavior, hidden
semantic labels, or unequal query budgets.

The experiment is intentionally small and exhaustive.  A later frozen run may replace
these two anonymous grammars with larger preregistered families without changing the
channel contract or outcome schema.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, random
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

SEED = 20260901
BUDGET = 2
X = (-3, -2, -1, 0, 1, 2, 3)

@dataclass(frozen=True)
class Candidate:
    opaque_id: str
    fn: Callable[[int], int]
    cost: int

@dataclass(frozen=True)
class Language:
    name: str
    candidates: Tuple[Candidate, ...]

# Same semantic hypothesis class, independently named/ordered source grammars.
M_A = Language("A", (
    Candidate("a7", lambda x: abs(x), 1),
    Candidate("a2", lambda x: x + 1, 2),
    Candidate("a9", lambda x: x * x, 3),
    Candidate("a4", lambda x: -x, 1),
))
M_B = Language("B", (
    Candidate("zeta", lambda x: -x, 1),
    Candidate("tau", lambda x: x * x, 3),
    Candidate("rho", lambda x: abs(x), 1),
    Candidate("mu", lambda x: x + 1, 2),
))
LANGUAGES = (M_A, M_B)

def target(x: int) -> int: return x * x

def error_vector(c: Candidate) -> Tuple[int, ...]:
    return tuple(abs(c.fn(x) - target(x)) for x in X)

def passed(c: Candidate) -> bool:
    return all(v == 0 for v in error_vector(c))

def residual_summary(c: Candidate) -> Tuple[int, int, int]:
    e = error_vector(c)
    return (sum(e), max(e), sum(v != 0 for v in e))

# Channel outputs are fixed-size integer tuples so byte length/stopping behavior cannot
# leak dose. PASS/FAIL is always the first coordinate; remaining coordinates are payload.
def genuine(c: Candidate) -> Tuple[int, int, int, int]:
    s, m, n = residual_summary(c)
    return (int(passed(c)), s, m, n)

def binary(c: Candidate) -> Tuple[int, int, int, int]:
    return (int(passed(c)), 0, 0, 0)

def localized(c: Candidate) -> Tuple[int, int, int, int]:
    e = error_vector(c)
    first = next((i + 1 for i, v in enumerate(e) if v), 0)
    return (int(passed(c)), first, 0, 0)

def scrubbed_factory(lang: Language):
    # Conditional on PASS/FAIL, deterministically permute genuine payloads among candidates.
    # This preserves the empirical payload multiset while breaking candidate->repair linkage.
    rows = [(c, genuine(c)) for c in lang.candidates]
    groups: Dict[int, List[Tuple[int,int,int]]] = {0: [], 1: []}
    for _, out in rows: groups[out[0]].append(out[1:])
    for k in groups: groups[k] = list(reversed(groups[k]))
    counters = {0: 0, 1: 0}
    table = {}
    for c, out in rows:
        k = out[0]; payloads = groups[k]
        payload = payloads[counters[k] % len(payloads)]
        counters[k] += 1
        table[c.opaque_id] = (k, *payload)
    return lambda c: table[c.opaque_id]

def permuted_factory(lang: Language):
    ids = list(lang.candidates)
    payload = [genuine(c) for c in ids]
    payload = payload[1:] + payload[:1]
    table = {c.opaque_id: p for c, p in zip(ids, payload)}
    return lambda c: table[c.opaque_id]

def score_from_channel(out: Tuple[int,int,int,int], cost: int) -> Tuple[int,int,int,int]:
    # Proposal policy sees ONLY channel output plus declared candidate cost.
    ok, a, b, c = out
    return (-ok, a + b + c, cost, 0)

def run_cell(lang: Language, channel_name: str, channel) -> dict:
    # Fixed full evaluation before selection prevents adaptive stopping leakage.
    observed = [(c, channel(c)) for c in lang.candidates]
    ranked = sorted(observed, key=lambda row: (score_from_channel(row[1], row[0].cost), row[0].opaque_id))
    tried = ranked[:BUDGET]
    success = any(passed(c) for c, _ in tried)
    return {
        "language": lang.name,
        "channel": channel_name,
        "budget": BUDGET,
        "ranked_ids": [c.opaque_id for c, _ in ranked],
        "tried_ids": [c.opaque_id for c, _ in tried],
        "success": success,
        "observations": [[c.opaque_id, list(out)] for c, out in observed],
    }

def leakage_audit(lang: Language, channels: dict) -> None:
    # Same candidate set, same budget, same output arity, no semantic success bit exposed
    # except the explicitly allowed PASS coordinate produced by the channel.
    ids = tuple(c.opaque_id for c in lang.candidates)
    assert len(set(ids)) == len(ids)
    for name, ch in channels.items():
        outs = [ch(c) for c in lang.candidates]
        assert all(len(o) == 4 for o in outs), name
        assert all(o[0] in (0,1) for o in outs), name
    assert BUDGET > 0 and BUDGET < len(lang.candidates)

def main() -> None:
    rows = []
    for lang in LANGUAGES:
        channels = {
            "V0_BINARY": binary,
            "V1_LOCALIZED": localized,
            "V2_GENUINE_RESIDUAL": genuine,
            "V3_SCRUBBED_INTERVENTION": scrubbed_factory(lang),
            "V4_PERMUTED_INTERVENTION": permuted_factory(lang),
        }
        leakage_audit(lang, channels)
        for name, ch in channels.items(): rows.append(run_cell(lang, name, ch))

    assert len(rows) == 10
    protocol = {
        "seed": SEED,
        "budget": BUDGET,
        "languages": [l.name for l in LANGUAGES],
        "channels": sorted({r["channel"] for r in rows}),
        "cells": rows,
        "interpretation": "Main effects estimate verifier-dose and meta-language dependence; interaction tests whether they are separable. Scrubbed/permuted arms are interventions, not MI-only controls.",
        "status": "HARNESS_ONLY_NOT_FROZEN_RESULT",
    }
    encoded = json.dumps(protocol, sort_keys=True, separators=(",", ":"))
    print(encoded)
    print("PROTOCOL_SHA256=" + sha256(encoded.encode()).hexdigest())

if __name__ == "__main__":
    main()
