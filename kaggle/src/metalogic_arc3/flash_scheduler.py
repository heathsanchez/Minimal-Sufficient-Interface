from __future__ import annotations

from collections import Counter

from .flash_ledger import GlobalLedger, Probe


def capability_demand(ledger: GlobalLedger) -> Counter[tuple]:
    out: Counter[tuple] = Counter()
    for residual in ledger.residuals.values():
        if residual.status != 'OPEN' or residual.demand_signature is None:
            continue
        out[tuple(residual.demand_signature)] += max(1, int(residual.estimated_cost))
    return out


def proposal_score(ledger: GlobalLedger, probe: Probe) -> float:
    open_residuals = [
        ledger.residuals[r]
        for r in probe.residuals_addressed
        if r in ledger.residuals and ledger.residuals[r].status == 'OPEN'
    ]
    protected = sum(3 for r in open_residuals if 'protected_progress' in r.potential_consequences)
    eliminable = sum(max(1, r.estimated_cost) for r in open_residuals)
    distinctions = sum(1 for r in open_residuals if 'settle_distinction' in r.potential_consequences)
    transfer = sum(1 for r in open_residuals if 'transfer' in r.potential_consequences)
    obstruction = sum(1 for r in open_residuals if 'obstruction' in r.potential_consequences)
    demand_map = capability_demand(ledger)
    demand = sum(demand_map[tuple(r.demand_signature)] for r in open_residuals if r.demand_signature is not None)
    cost = max(1, int(probe.expected_cost))
    return (3*protected + eliminable + 2*distinctions + 2*transfer + 2*obstruction + 0.05*demand) / cost


def choose_wave(ledger: GlobalLedger, *, width: int = 4) -> list[Probe]:
    rows = []
    for probe in ledger.probes.values():
        if probe.status != 'PENDING':
            continue
        score = proposal_score(ledger, probe)
        rows.append((score, -probe.expected_cost, probe.game, probe.probe_id, probe))
    rows.sort(reverse=True, key=lambda row: row[:4])
    chosen: list[Probe] = []
    covered: set[str] = set()
    for _score, _negcost, _game, _pid, probe in rows:
        if probe.residuals_addressed & covered:
            continue
        chosen.append(probe)
        covered |= probe.residuals_addressed
        if len(chosen) >= width:
            break
    return chosen
