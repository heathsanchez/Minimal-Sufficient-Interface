#!/usr/bin/env python3
"""Typed repair-plan AST constructed from source-visible recursive shape.

Finite structural proof-plan experiment. This is not autonomous invention of
the underlying induction/elimination semantics, which remain supplied.
"""
import dataclasses,hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).parent
@dataclasses.dataclass(frozen=True)
class Plan:
    recursor:str
    constructors:tuple
    recursive_fields:tuple
    action:str
    def data(self):return dataclasses.asdict(self)
def construct(source):
    m=re.search(r"inductive\s+(\w+)\s*\([^)]*\)\s+where([\s\S]*?)(?:\n(?:deriving|def)\b)",source)
    if not m:raise ValueError("no inductive declaration")
    typ,block=m.groups()
    ctors=[]
    for line in block.splitlines():
        t=re.match(r"\s*\|\s*(\w+)\s*:\s*(.+)",line)
        if t:ctors.append((t.group(1),t.group(2)))
    if len(ctors)<2:raise ValueError("no branching constructor evidence")
    recursive=[]
    for name,signature in ctors:
        parts=re.split(r"\s+→\s+",signature)
        if len(parts)<2 or parts[-1].strip()!=f"{typ} α":
            raise ValueError(f"unsupported constructor result type: {name}: {signature}")
        n=sum(part.strip()==f"{typ} α" for part in parts[:-1])
        recursive.append((name,n))
    if not recursive:raise ValueError("no recursive fields")
    if not any(n>=2 for _,n in recursive):raise ValueError("no branching recursion")
    return Plan(typ,tuple(x for x,_ in ctors),tuple(recursive),"structural_induction_with_one_IH_per_recursive_field")
def run():
    source=ROOT/"FrozenSource.lean"
    tasks=ROOT/"frozen_tasks.json"
    plan=construct(source.read_text())
    receipt={"plan":plan.data(),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
      "task_sha256":hashlib.sha256(tasks.read_bytes()).hexdigest()}
    receipt["digest"]=hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()).hexdigest()
    out=ROOT/"results";out.mkdir(exist_ok=True)
    (out/"constructed_plan.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    report={"status":"CANDIDATE_TYPED_BRANCHING_PLAN_CONSTRUCTION",
      "constructed_plan":plan.data(),"receipt":receipt["digest"],
      "supplied_semantics":["Lean structural induction","induction hypotheses","simp","omega"],
      "new_semantics_invented":False,"protected_proofs_generated":0,
      "claims":{"source_derived_branching_plan":"CANDIDATE",
        "autonomous_meta_constructor":"UNKNOWN",
        "advantage_over_Lean_induction":"REJECTED_ON_THIS_CASE"}}
    (out/"constructor_evidence.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":run()
