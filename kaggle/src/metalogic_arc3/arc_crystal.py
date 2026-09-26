from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable

Role=tuple[Hashable,...]

@dataclass(frozen=True)
class CapabilityEvidence:
    role: Role
    outcome: str
    source: str
    consequence_grade: int=0

@dataclass(frozen=True)
class Capability:
    role: Role
    outcome: str
    supports: tuple[str,...]
    grade: int

class ArcCrystal:
    """Conflict-preserving ARC-3 capability memory.

    Nothing becomes reusable merely because it is frequent. A role is reusable
    only while every admitted observation agrees. Conflict demotes it to UNKNOWN.
    """
    def __init__(self)->None:
        self._outcomes:dict[Role,dict[str,set[str]]]=defaultdict(lambda:defaultdict(set))
        self._grades:dict[tuple[Role,str],int]=defaultdict(int)

    def observe(self,e:CapabilityEvidence)->None:
        r=tuple(e.role); o=str(e.outcome)
        self._outcomes[r][o].add(str(e.source))
        self._grades[(r,o)]=max(self._grades[(r,o)],int(e.consequence_grade))

    def predict(self,role:Role)->str|None:
        vals=self._outcomes.get(tuple(role),{})
        if len(vals)!=1:return None
        return next(iter(vals))

    def capability(self,role:Role)->Capability|None:
        r=tuple(role); o=self.predict(r)
        if o is None:return None
        return Capability(r,o,tuple(sorted(self._outcomes[r][o])),self._grades[(r,o)])

    def conflicted(self,role:Role)->bool:
        return len(self._outcomes.get(tuple(role),{}))>1

    def snapshot(self)->dict:
        stable=sum(1 for r in self._outcomes if self.predict(r) is not None)
        conflicts=sum(1 for r in self._outcomes if self.conflicted(r))
        return {"roles":len(self._outcomes),"stable":stable,"conflicts":conflicts}

    @staticmethod
    def conservative_separator(hypotheses:Iterable[str],actions:Iterable[tuple],
                               predictions:dict[tuple[str,tuple],str|None]):
        hs=tuple(dict.fromkeys(map(str,hypotheses))); acts=tuple(dict.fromkeys(actions))
        scored=[]
        for a in acts:
            counts=Counter(); unknown=0
            for h in hs:
                y=predictions.get((h,a))
                if y is None:unknown+=1
                else:counts[y]+=1
            upper=max(counts.values(),default=0)+unknown
            scored.append((upper,unknown,repr(a),a))
        return min(scored) if scored else None

    @staticmethod
    def next_acquisition(hypotheses:Iterable[str],actions:Iterable[tuple],
                         roles:dict[tuple[str,tuple],Role],crystal:"ArcCrystal"):
        """Buy the UNKNOWN role with greatest coverage on the best action frontier."""
        hs=tuple(map(str,hypotheses)); acts=tuple(actions)
        predictions={(h,a):crystal.predict(roles[(h,a)]) for h in hs for a in acts}
        ranked=[]
        for a in acts:
            counts=Counter(y for (h,aa),y in predictions.items() if aa==a and y is not None)
            unknown=sum(1 for h in hs if predictions[(h,a)] is None)
            ranked.append((max(counts.values(),default=0)+unknown,unknown,repr(a),a))
        ranked.sort()
        frontier={row[3] for row in ranked[:min(12,len(ranked))]}
        freq=Counter()
        for h in hs:
            for a in frontier:
                r=roles[(h,a)]
                if crystal.predict(r) is None:freq[r]+=1
        return max(freq,key=lambda r:(freq[r],repr(r))) if freq else None
