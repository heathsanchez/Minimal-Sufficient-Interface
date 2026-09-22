"""Consequence-first memory: lineage stores what happened; live memory stores what works."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Hashable, Mapping, Sequence
from consequence_compiler import CompilerSpec, compile_consequences

Feature = Hashable

@dataclass(frozen=True)
class Consequence:
    progress: int
    changed: bool
    terminal: str = "CONTINUE"
    @property
    def key(self):
        return (self.progress, self.changed, self.terminal)

@dataclass(frozen=True)
class Episode:
    eid: str
    surface: str
    intervention: str
    features: tuple[tuple[str, Feature], ...]
    consequence: Consequence
    @classmethod
    def make(cls, eid, surface, intervention, features, consequence):
        return cls(eid, surface, intervention, tuple(sorted(features.items())), consequence)
    def row(self):
        return dict(self.features)

@dataclass(frozen=True)
class Residual:
    intervention: str
    positive: tuple[str, ...]
    negative: tuple[str, ...]
    consequence: tuple
    reason: str

@dataclass(frozen=True)
class Law:
    intervention: str
    consequence: Consequence
    guard: tuple[tuple[str, Feature], ...]
    support: int
    surfaces: int
    def applies(self, row):
        return all(row.get(k) == v for k, v in self.guard)
    def live(self):
        return {
            "intervention": self.intervention,
            "consequence": self.consequence.key,
            "guard": self.guard,
            "support": self.support,
            "surfaces": self.surfaces,
        }

def stable(episodes: Sequence[Episode]):
    if not episodes:
        return ()
    rows = [e.row() for e in episodes]
    names = set(rows[0])
    for r in rows[1:]:
        names &= set(r)
    return tuple((k, rows[0][k]) for k in sorted(names)
                 if all(r[k] == rows[0][k] for r in rows))

def matches(e: Episode, guard):
    r = e.row()
    return all(r.get(k) == v for k, v in guard)

def minimum_guard(pos, neg):
    cands = stable(pos)
    if not neg:
        return ()
    for n in range(len(cands) + 1):
        for g in combinations(cands, n):
            if all(not matches(e, g) for e in neg):
                return tuple(g)
    return None

class Atlas:
    def __init__(self, min_support=2, min_surfaces=2):
        self.min_support = min_support
        self.min_surfaces = min_surfaces
        self.lineage = ()
        self.laws = ()
        self.residuals = ()

    def append(self, e: Episode):
        if any(x.eid == e.eid for x in self.lineage):
            raise ValueError("duplicate episode")
        self.lineage += (e,)
        self.reclose()

    def reclose(self):
        groups = {}
        for e in self.lineage:
            groups.setdefault((e.intervention, e.consequence.key), []).append(e)
        laws, residuals = [], []
        for (intervention, key), pos in groups.items():
            surfaces = {e.surface for e in pos}
            if len(pos) < self.min_support or len(surfaces) < self.min_surfaces:
                continue
            neg = [e for e in self.lineage
                   if e.intervention == intervention and e.consequence.key != key]
            guard = minimum_guard(pos, neg)
            if guard is None:
                residuals.append(Residual(
                    intervention,
                    tuple(e.eid for e in pos),
                    tuple(e.eid for e in neg),
                    key,
                    "current observation language collapses histories with different protected consequences",
                ))
            else:
                laws.append(Law(intervention, pos[0].consequence, guard, len(pos), len(surfaces)))
        self.laws = tuple(sorted(laws, key=lambda x: (x.intervention, x.consequence.key, x.guard)))
        self.residuals = tuple(sorted(residuals, key=lambda x: (x.intervention, x.consequence)))

    def live(self):
        return tuple(x.live() for x in self.laws)

    def predict(self, intervention, row):
        return tuple(x.consequence for x in self.laws
                     if x.intervention == intervention and x.applies(row))

    def compile_lens(self, residual: Residual, candidates: Mapping[str, Mapping[str, Feature]]):
        ids = residual.positive + residual.negative
        by = {e.eid: e for e in self.lineage}
        target = residual.consequence
        def action(i): return by[i].intervention
        def protected(i): return by[i].consequence.key == target
        realizers = {name: (lambda i, values=values: values[i])
                     for name, values in candidates.items()}
        return compile_consequences(CompilerSpec(
            name="consequence-forced-lens",
            carrier=ids,
            interface={"intervention": action},
            protected={"protected": protected},
            realizers=realizers,
        ))

def demo():
    works = Consequence(1, True)
    blocked = Consequence(0, False)
    a = Atlas()
    for e in (
        Episode.make("e1", "pixels", "advance", {"color":"red","x":2,"scale":1}, works),
        Episode.make("e2", "objects", "advance", {"color":"blue","x":17,"scale":3}, works),
        Episode.make("e3", "graph", "advance", {"color":"green","x":-4,"scale":2}, works),
    ):
        a.append(e)
    assert a.live() == ({
        "intervention":"advance","consequence":works.key,"guard":(),
        "support":3,"surfaces":3
    },)
    assert a.predict("advance", {"color":"orange","x":999,"scale":9}) == (works,)

    a.append(Episode.make("e4","new","advance",{"color":"black","x":0,"scale":7},blocked))
    r = next(x for x in a.residuals if x.consequence == works.key)
    candidates = {
        "color":{"e1":"red","e2":"blue","e3":"green","e4":"black"},
        "position":{"e1":"left","e2":"right","e3":"left","e4":"middle"},
        "scale_parity":{"e1":1,"e2":1,"e3":0,"e4":1},
        "gate_relation":{"e1":"open","e2":"open","e3":"open","e4":"blocked"},
    }
    report = a.compile_lens(r, candidates)
    assert report.lawful_realizers == ("gate_relation",)

    b = Atlas()
    for e in a.lineage:
        row = e.row()
        row["gate_relation"] = candidates["gate_relation"][e.eid]
        b.append(Episode.make(e.eid,e.surface,e.intervention,row,e.consequence))
    good = [x for x in b.laws if x.consequence == works]
    assert len(good) == 1 and good[0].guard == (("gate_relation","open"),)
    assert b.predict("advance", {"gate_relation":"open","color":"purple"}) == (works,)
    assert works not in b.predict("advance", {"gate_relation":"blocked","color":"purple"})
    live_text = repr(b.live())
    assert all(t not in live_text for t in ("pixels","objects","graph","e1","e2","e3","e4"))
    return {
        "status":"PASS",
        "lineage_events":len(b.lineage),
        "episodes_in_live_memory":0,
        "initial_law_was_surface_free":True,
        "counterexample_created_representation_residual":True,
        "residual_forced_lens":report.lawful_realizers,
        "compiled_live_memory":b.live(),
        "heldout_transport":True,
    }

if __name__ == "__main__":
    import json
    print("CONSEQUENTIAL_ATLAS_V0=" + json.dumps(demo(), sort_keys=True, default=str))
