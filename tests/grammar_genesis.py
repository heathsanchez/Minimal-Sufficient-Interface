"""Bounded, target-blind grammar acquisition on the complete Boolean domain.

The learner is independent of task names and truth tables. The trusted oracle
owns the target and supplies observations. A finite exhaustive checker, not
sample agreement, authorizes installation. This is a deliberately finite
representation-change experiment, not unrestricted program synthesis.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from collections import deque

MASK = 15
DOMAIN = ((0, 0), (0, 1), (1, 0), (1, 1))
INPUTS = (0, 15, 12, 10)
MAX_GATES = 4

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

@dataclass(frozen=True)
class Gate:
    op: str
    args: tuple[int, ...]

@dataclass(frozen=True)
class Program:
    gates: tuple[Gate, ...]
    output: int

@dataclass(frozen=True)
class Certificate:
    arity: int
    table: tuple[int, ...]
    dependencies: tuple[str, ...]
    identity: str

@dataclass(frozen=True)
class State:
    archive: tuple[Certificate, ...] = ()
    bound: int = MAX_GATES

def bit(table, x, y):
    return (table >> (2*x+y)) & 1

def apply(table, arity, args):
    index = 0
    for a in args:
        index = (index << 1) | a
    return (table >> index) & 1

def gate_mask(table, arity, args):
    result = 0
    for x, y in DOMAIN:
        result |= apply(table, arity, tuple(bit(a, x, y) for a in args)) << (2*x+y)
    return result

def operations(state):
    ops = {"not": (1, 1)}
    for cert in state.archive:
        ops[cert.identity] = (cert.arity, sum(v << i for i, v in enumerate(cert.table)))
    return ops

def evaluate(program, state):
    if not isinstance(program, Program) or len(program.gates) > state.bound:
        raise ValueError("Invalid source bound")
    wires = list(INPUTS)
    ops = operations(state)
    for gate in program.gates:
        if gate.op not in ops:
            raise ValueError("Uncertified operator")
        arity, table = ops[gate.op]
        if len(gate.args) != arity or any(type(i) is not int or i < 0 or i >= len(wires) for i in gate.args):
            raise ValueError("Invalid dependency")
        wires.append(gate_mask(table, arity, tuple(wires[i] for i in gate.args)))
    if type(program.output) is not int or not 0 <= program.output < len(wires):
        raise ValueError("Invalid output")
    return wires[program.output]

def exact_search(state, target):
    """Shortest-gate BFS, deduplicated by available semantic wire sets."""
    if state.bound != MAX_GATES or len({c.identity for c in state.archive}) != len(state.archive):
        raise ValueError("Invalid state")
    ops = operations(state)
    for i, value in enumerate(INPUTS):
        if value == target:
            return Program((), i)
    queue = deque([((), INPUTS)])
    seen = {tuple(sorted(set(INPUTS)))}
    while queue:
        gates, wires = queue.popleft()
        if len(gates) == state.bound:
            continue
        for op, (arity, table) in ops.items():
            from itertools import product
            for args in product(range(len(wires)), repeat=arity):
                value = gate_mask(table, arity, tuple(wires[i] for i in args))
                if value in wires:
                    continue
                next_gates = gates + (Gate(op, args),)
                next_wires = wires + (value,)
                p = Program(next_gates, len(wires))
                if value == target:
                    return p
                key = tuple(sorted(set(next_wires)))
                if key not in seen:
                    seen.add(key)
                    queue.append((next_gates, next_wires))
    return None

def unary_functions():
    return set(INPUTS) | {MASK ^ x for x in INPUTS}

def necessary_arity(table):
    if table in unary_functions():
        return 0
    return 2

def synthesize(oracle):
    """Infer the least missing arity and its complete table, without target names."""
    observed = tuple(oracle.query(x, y) for x, y in DOMAIN)
    if any(type(v) is not int or v not in (0, 1) for v in observed):
        raise ValueError("Non-Boolean observation")
    table = sum(v << i for i, v in enumerate(observed))
    arity = necessary_arity(table)
    if arity == 0:
        return None
    return oracle.certify((arity, observed))

class TrustedOracle:
    def __init__(self, target):
        if type(target) is not int or not 0 <= target <= MASK:
            raise ValueError("Invalid target")
        self.target = target

    def query(self, x, y):
        return bit(self.target, x, y)

    def certify(self, proposal):
        arity, table = proposal
        if arity != 2 or len(table) != 4 or any(v not in (0, 1) for v in table):
            raise ValueError("Invalid repair")
        if tuple(self.query(x, y) for x, y in DOMAIN) != tuple(table):
            raise ValueError("Incorrect semantic repair")
        if necessary_arity(self.target) != arity:
            raise ValueError("Unnecessary arity")
        identity = "cert-" + digest((arity, table, ()))
        return Certificate(arity, tuple(table), (), identity)

def install(state, certificate, oracle):
    if state.bound != MAX_GATES or not isinstance(certificate, Certificate):
        raise ValueError("Invalid state or certificate")
    checked = oracle.certify((certificate.arity, certificate.table))
    if checked != certificate or certificate.identity in {c.identity for c in state.archive}:
        raise ValueError("Invalid or duplicate certificate")
    return State(state.archive + (certificate,), state.bound)

def qualification(acquisition, heldout):
    frozen = State()
    old_acquisition = exact_search(frozen, acquisition)
    old_heldout = exact_search(frozen, heldout)
    if old_acquisition is not None:
        raise ValueError("Acquisition already expressible")
    cert = synthesize(TrustedOracle(acquisition))
    if cert is None:
        raise ValueError("No necessary repair")
    acquired = install(frozen, cert, TrustedOracle(acquisition))
    first = exact_search(acquired, acquisition)
    transfer = exact_search(acquired, heldout)
    assert first is not None and evaluate(first, acquired) == acquisition
    assert transfer is not None and evaluate(transfer, acquired) == heldout
    assert old_heldout is None
    assert exact_search(frozen, heldout) is None
    return {"before": frozen, "after": acquired, "certificate": cert,
            "acquisition": first, "transfer": transfer, "ablation": old_heldout,
            "source_bound": MAX_GATES, "exhaustive_domain": True,
            "unrestricted_genesis": False}

def encode_program(program):
    return {"gates": [{"op": g.op, "args": list(g.args)} for g in program.gates],
            "output": program.output}

def result_json(result):
    return {"source_bound": result["source_bound"],
            "certificate": result["certificate"].__dict__,
            "acquisition": encode_program(result["acquisition"]),
            "transfer": encode_program(result["transfer"]),
            "exhaustive_domain": True, "ablation": "unreachable",
            "unrestricted_genesis": False}
