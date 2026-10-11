#!/usr/bin/env python3
"""V4 source-bound old-grammar obstruction; no new constructor claimed."""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).parent
V3=ROOT.parent/"bundy_critic_induction_v3"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    source=ROOT/"FrozenSource.lean"
    tasks=ROOT/"frozen_tasks.json"
    old=V3/"generate_proofs.py"
    assert source.exists() and tasks.exists() and old.exists()
    code=old.read_text()
    # Exhaustively enumerate V3's actual syntactic candidate families:
    # its interpreter only accepts append, Nat addition and multiplication,
    # and emits List-based induction. This is a source-relative grammar claim.
    allowed=re.findall(r'if op=="([^"]+)"|elif op=="([^"]+)"',code)
    operators=sorted({v for pair in allowed for v in pair if v})
    old_list_induction="induction xs generalizing acc" in code
    old_has_tree_constructor=bool(re.search(r'\bTree\b|\.node\b',code))
    result={"status":"WARRANTED_SOURCE_RELATIVE_GRAMMAR_OBSTRUCTION",
      "old_source_sha256":sha(old),"new_source_sha256":sha(source),
      "frozen_tasks_sha256":sha(tasks),
      "old_operators":operators,
      "old_list_induction":old_list_induction,
      "old_has_tree_constructor":old_has_tree_constructor,
      "new_constructor_generated":False,
      "protected_proofs_generated":0,
      "claims":{"v3_grammar_cannot_express_tree_branching":"SOURCE_RELATIVE",
        "semantic_inexpressibility_of_all_old_proof_programs":"UNKNOWN",
        "autonomous_critic_genesis":"UNKNOWN"}}
    assert old_list_induction and not old_has_tree_constructor
    assert operators==["add","append","mul"],operators
    out=ROOT/"results";out.mkdir(exist_ok=True)
    (out/"obstruction.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":run()
