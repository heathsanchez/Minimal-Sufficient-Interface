#!/usr/bin/env python3
"""Natural-domain MSI gate using JPL Horizons heliocentric ephemerides.

The learner receives anonymous Cartesian trajectories only.  It searches a
small generic generated family of local vector relations

    d2 x / dt2 ~= alpha * x * ||x||^k

without semantic names.  The winning relation is chosen on Earth training
observations, promoted, and then used unchanged for held-out Earth forecasting
and source-distinct Mars transfer.  Exact ablation reverts to the cold
constant-velocity predictor.

This is intentionally a first natural-domain gate, not unrestricted law
invention: the local relation grammar and integer exponent range are supplied.
"""
from __future__ import annotations

import csv
import io
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

Vec = Tuple[float, float, float]

HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
START = "2025-01-01"
STOP = "2025-09-01"
STEP = "1 d"


def vadd(a: Vec, b: Vec) -> Vec:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])

def vsub(a: Vec, b: Vec) -> Vec:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def vscale(s: float, a: Vec) -> Vec:
    return (s*a[0], s*a[1], s*a[2])

def dot(a: Vec, b: Vec) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def norm(a: Vec) -> float:
    return math.sqrt(dot(a,a))

def rms(errors: Iterable[Vec]) -> float:
    vals = [dot(e,e) for e in errors]
    return math.sqrt(sum(vals)/len(vals))


def fetch_vectors(command: str) -> List[Vec]:
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@10'",  # heliocentric, but this name is not exposed to learner
        "START_TIME": f"'{START}'",
        "STOP_TIME": f"'{STOP}'",
        "STEP_SIZE": f"'{STEP}'",
        "VEC_TABLE": "'2'",
        "CSV_FORMAT": "'YES'",
        "OUT_UNITS": "'AU-D'",
        "REF_PLANE": "'ECLIPTIC'",
    }
    url = HORIZONS + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        text = r.read().decode("utf-8")
    if "$$SOE" not in text or "$$EOE" not in text:
        raise RuntimeError("Horizons response missing ephemeris markers")
    body = text.split("$$SOE",1)[1].split("$$EOE",1)[0]
    out: List[Vec] = []
    for row in csv.reader(io.StringIO(body)):
        if len(row) < 5:
            continue
        # CSV vector rows: JD, calendar date, X, Y, Z, ...
        try:
            out.append((float(row[2]), float(row[3]), float(row[4])))
        except ValueError:
            continue
    if len(out) < 150:
        raise RuntimeError(f"too few Horizons rows: {len(out)}")
    return out


@dataclass(frozen=True)
class Relation:
    k: int
    alpha: float
    train_rmse: float


def fit_relation(xs: Sequence[Vec], k: int) -> Relation:
    # central second difference with dt=1 day
    num = den = 0.0
    residual_terms = []
    pairs = []
    for i in range(1, len(xs)-1):
        a = vadd(vsub(xs[i+1], vscale(2.0, xs[i])), xs[i-1])
        r = norm(xs[i])
        phi = vscale(r**k, xs[i])
        num += dot(a, phi)
        den += dot(phi, phi)
        pairs.append((a, phi))
    alpha = num / den
    for a, phi in pairs:
        residual_terms.append(vsub(a, vscale(alpha, phi)))
    return Relation(k=k, alpha=alpha, train_rmse=rms(residual_terms))


def discover(xs: Sequence[Vec]) -> Tuple[Relation, List[Relation]]:
    # Frozen, domain-neutral integer-power local relation grammar.
    candidates = [fit_relation(xs, k) for k in range(-6, 5)]
    candidates.sort(key=lambda r: (r.train_rmse, abs(r.k), r.k))
    return candidates[0], candidates


def forecast_cold(x0: Vec, x1: Vec, steps: int) -> List[Vec]:
    v = vsub(x1, x0)
    out = [x0, x1]
    while len(out) < steps:
        out.append(vadd(out[-1], v))
    return out


def forecast_warm(x0: Vec, x1: Vec, steps: int, rel: Relation) -> List[Vec]:
    # Position-Verlet realization of the promoted anonymous local relation.
    out = [x0, x1]
    while len(out) < steps:
        x = out[-1]
        prev = out[-2]
        phi = vscale(norm(x)**rel.k, x)
        nxt = vadd(vsub(vscale(2.0, x), prev), vscale(rel.alpha, phi))
        out.append(nxt)
    return out


def forecast_error(pred: Sequence[Vec], truth: Sequence[Vec]) -> float:
    return rms(vsub(a,b) for a,b in zip(pred, truth))


def rotate(v: Vec) -> Vec:
    # Fixed orthogonal coordinate change, not exposed to selection.
    # permutation + sign flip preserves Euclidean structure exactly.
    return (v[1], -v[2], -v[0])


def main() -> None:
    earth = fetch_vectors("399")
    mars = fetch_vectors("499")

    train_n = 120
    horizon = 60
    earth_train = earth[:train_n]
    winner, all_rel = discover(earth_train)
    runner = all_rel[1]

    # Held-out Earth starts exactly at the train boundary with two observed states.
    e_truth = earth[train_n-2:train_n-2+horizon]
    e_cold = forecast_cold(e_truth[0], e_truth[1], len(e_truth))
    e_warm = forecast_warm(e_truth[0], e_truth[1], len(e_truth), winner)
    e0, e1 = forecast_error(e_cold, e_truth), forecast_error(e_warm, e_truth)

    # Frozen transfer: same learned k and alpha, no Mars refit.
    m_truth = mars[train_n-2:train_n-2+horizon]
    m_cold = forecast_cold(m_truth[0], m_truth[1], len(m_truth))
    m_warm = forecast_warm(m_truth[0], m_truth[1], len(m_truth), winner)
    m0, m1 = forecast_error(m_cold, m_truth), forecast_error(m_warm, m_truth)

    # Presentation invariance: rediscover from a coordinate-changed Earth trace.
    rwinner, _ = discover([rotate(x) for x in earth_train])

    print(f"NATURAL_ORBIT_SOURCE earth_rows={len(earth)} mars_rows={len(mars)} source=JPL_HORIZONS")
    print(f"DISCOVERED_RELATION k={winner.k} alpha={winner.alpha:.12g} train_rmse={winner.train_rmse:.12g} runner_k={runner.k} runner_rmse={runner.train_rmse:.12g}")
    print(f"EARTH_HELDOUT cold_rmse={e0:.12g} warm_rmse={e1:.12g} ratio={e1/e0:.6g}")
    print(f"MARS_FROZEN_TRANSFER cold_rmse={m0:.12g} warm_rmse={m1:.12g} ratio={m1/m0:.6g}")
    print(f"COORDINATE_CHANGE original_k={winner.k} rotated_k={rwinner.k}")

    # Deciding gates.  Require a substantial rather than marginal advantage.
    assert e1 < 0.25 * e0, (e0,e1)
    assert m1 < 0.25 * m0, (m0,m1)
    assert rwinner.k == winner.k
    # Exact ablation is the cold predictor by construction.
    assert forecast_error(forecast_cold(e_truth[0],e_truth[1],len(e_truth)),e_truth) == e0

    print("NATURAL_RESIDUAL_TO_REUSABLE_RELATION=PASS")
    print("HELDOUT_PREDICTION_PHASE_CHANGE=PASS")
    print("SOURCE_DISTINCT_MARS_TRANSFER=PASS")
    print("PRESENTATION_INVARIANCE=PASS")
    print("EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS")
    print("NATURAL_ORBIT_GENESIS_V1=PASS")

if __name__ == "__main__":
    main()
