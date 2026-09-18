from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .flash_ledger import FlashLedger, OPEN, PENDING, Probe


@dataclass(frozen=True)
class ProbeScore:
    probe_id: str
    score: float
    demand: float
    eliminable_cost: int
    protected_weight: float
    transfer_weight: float
    obstruction_weight: float


def capability_demand(ledger: FlashLedger) -> dict[str, float]:
    demand: dict[str, float] = defaultdict(float)
    for residual in ledger.residuals.values():
        if residual.status != OPEN:
            continue
        if residual.demand_key:
            demand[residual.demand_key] += max(1, int(residual.estimated_cost))
        for key in residual.potential_consequences:
            demand[key] += max(1, int(residual.estimated_cost))
    return dict(demand)


def score_probe(ledger: FlashLedger, probe: Probe) -> ProbeScore:
    if probe.status != PENDING:
        return ProbeScore(probe.probe_id, float("-inf"), 0.0, 0, 0.0, 0.0, 0.0)

    demand_map = capability_demand(ledger)
    residuals = [
        ledger.residuals[rid]
        for rid in sorted(probe.residuals_addressed)
        if rid in ledger.residuals and ledger.residuals[rid].status == OPEN
    ]
    eliminable = sum(max(1, int(r.estimated_cost)) for r in residuals)
    demand = sum(
        demand_map.get(r.demand_key or "", 0.0)
        + sum(demand_map.get(key, 0.0) for key in r.potential_consequences)
        for r in residuals
    )

    protected = float(probe.metadata.get("protected_progress_potential", 0.0))
    transfer = float(probe.metadata.get("transfer_potential", 0.0))
    obstruction = float(probe.metadata.get("obstruction_potential", 0.0))
    distinctions = float(probe.metadata.get("distinctions_settleable", len(residuals)))
    expected_cost = max(1, int(probe.expected_cost))

    numerator = (
        5.0 * protected
        + float(eliminable)
        + 0.35 * demand
        + 1.5 * distinctions
        + 2.0 * transfer
        + 2.5 * obstruction
    )
    return ProbeScore(
        probe.probe_id,
        numerator / expected_cost,
        demand,
        eliminable,
        protected,
        transfer,
        obstruction,
    )


def ranked_pending_probes(ledger: FlashLedger) -> list[ProbeScore]:
    rows = [
        score_probe(ledger, probe)
        for probe in ledger.probes.values()
        if probe.status == PENDING
    ]
    rows.sort(key=lambda row: (-row.score, row.probe_id))
    return rows


def choose_wave(
    ledger: FlashLedger,
    *,
    capacity: int,
    max_overlap: float = 0.0,
) -> list[str]:
    """Choose a deterministic low-overlap wave from the global residual market."""
    if capacity <= 0:
        return []

    chosen: list[str] = []
    covered: set[str] = set()
    for row in ranked_pending_probes(ledger):
        probe = ledger.probes[row.probe_id]
        addressed = set(probe.residuals_addressed)
        overlap = len(addressed & covered) / max(1, len(addressed)) if addressed else 0.0
        if overlap > max_overlap:
            continue
        chosen.append(probe.probe_id)
        covered.update(addressed)
        if len(chosen) >= capacity:
            break
    return chosen
