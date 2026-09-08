"""Independent exhaustive checker for the finite grammar experiment."""
from hashlib import sha256
import json

DOMAIN = ((0,0),(0,1),(1,0),(1,1))
SEED = ((0,0,0,0),(1,1,1,1),(0,0,1,1),(0,1,0,1))

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def evaluate(program, certificate=None):
    wires = list(SEED)
    if len(program["gates"]) > 4:
        raise ValueError("Source bound")
    for gate in program["gates"]:
        op, args = gate["op"], gate["args"]
        if not isinstance(args, list) or any(type(i) is not int or not 0 <= i < len(wires) for i in args):
            raise ValueError("Forward or invalid wire")
        if op == "not" and len(args) == 1:
            value = tuple(1-v for v in wires[args[0]])
        elif certificate is not None and op == certificate["identity"] and len(args) == certificate["arity"]:
            table = certificate["table"]
            value = []
            for row in range(4):
                index = 0
                for i in args:
                    index = 2*index + wires[i][row]
                value.append(table[index])
            value = tuple(value)
        else:
            raise ValueError("Unknown or malformed operator")
        wires.append(value)
    output = program["output"]
    if type(output) is not int or not 0 <= output < len(wires):
        raise ValueError("Invalid output")
    return wires[output]

def check(report, acquisition, heldout):
    c = report["certificate"]
    if report["source_bound"] != 4 or c["arity"] != 2 or tuple(c["dependencies"]) != ():
        raise ValueError("Invalid scope")
    if len(c["table"]) != 4 or any(type(v) is not int or v not in (0,1) for v in c["table"]):
        raise ValueError("Invalid table")
    expected_id = "cert-" + digest((c["arity"], tuple(c["table"]), ()))
    if c["identity"] != expected_id:
        raise ValueError("Certificate identity mismatch")
    acquisition = tuple(acquisition)
    heldout = tuple(heldout)
    if tuple(c["table"]) != acquisition:
        raise ValueError("Acquisition certificate mismatch")
    unary = set(SEED) | {tuple(1-v for v in t) for t in SEED}
    if acquisition in unary or heldout in unary:
        raise ValueError("Old grammar already sufficient")
    if evaluate(report["acquisition"], c) != acquisition:
        raise ValueError("Acquisition replay failed")
    if evaluate(report["transfer"], c) != heldout:
        raise ValueError("Held-out replay failed")
    # Every old circuit is unary: constants/projections are unary and NOT
    # preserves that property. This exhausts all six possible old functions.
    for table in unary:
        if table == acquisition or table == heldout:
            raise ValueError("Ablation failed")
    return True
