from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass

@dataclass(frozen=True)
class FutureEvidence:
    outcome: str
    source: str
    features: tuple[tuple[str,str],...]

def context(**features):
    return tuple(sorted((str(k),repr(v)) for k,v in features.items()))

class ProtectedFutureKernel:
    """Collatz-style residual/refinement loop for one ARC capability.

    Begin maximally compressed. Conflicting protected outcomes create the live
    residual kernel. Admit a coordinate only when it removes every current
    conflict cell, then reclose all retained evidence through that quotient.
    """
    def __init__(self):
        self.rows=[]
        self.separators=()

    def observe(self,outcome,source,features=()):
        self.rows.append(FutureEvidence(str(outcome),str(source),tuple(features)))

    def _cells(self,separators=None):
        seps=self.separators if separators is None else tuple(separators)
        cells=defaultdict(lambda:{"outcomes":set(),"sources":set()})
        for row in self.rows:
            f=dict(row.features)
            key=tuple((k,f.get(k,"<UNKNOWN>")) for k in seps)
            cells[key]["outcomes"].add(row.outcome)
            cells[key]["sources"].add(row.source)
        return cells

    def residual_kernel(self):
        return tuple(
            {"cell":key,"outcomes":tuple(sorted(v["outcomes"])),
             "sources":tuple(sorted(v["sources"]))}
            for key,v in sorted(self._cells().items(),key=lambda kv:repr(kv[0]))
            if len(v["outcomes"])>1
        )

    def predict(self,features=()):
        f=dict(features)
        key=tuple((k,f.get(k,"<UNKNOWN>")) for k in self.separators)
        outcomes=self._cells().get(key,{}).get("outcomes",set())
        return next(iter(outcomes)) if len(outcomes)==1 else None

    def cheapest_separator(self,candidates):
        if not self.residual_kernel():
            return None
        for name in map(str,candidates):
            if name in self.separators:
                continue
            cells=self._cells(self.separators+(name,))
            if cells and all(len(v["outcomes"])<=1 for v in cells.values()):
                return name
        return None

    def refine(self,candidates):
        sep=self.cheapest_separator(candidates)
        if sep is not None:
            self.separators=self.separators+(sep,)
        return sep

    @property
    def expressive_obstruction(self):
        return bool(self.residual_kernel())
