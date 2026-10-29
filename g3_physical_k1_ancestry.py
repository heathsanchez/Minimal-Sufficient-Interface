"""Small, checkable bridge from learned K1 programs to recursive constructors.

This does not discover a new domain. It removes a causal shortcut in the
historical synthetic witness: recursive doubling must consume the actual
source-grammar expressions discovered and verified at the prior stage.
"""


class BudgetExceeded(ValueError):
    """The executable source-language certificate exceeds the fixed budget."""


class InvalidCertificate(ValueError):
    """The proposed program or its claimed semantics failed independent checks."""


def compile_promoted_block(grammar, selected, programs, first_mask, second_mask, *, budget):
    """Promote two verified 3-input formulas into one executable block.

    Grammar operations and selected anonymous truth tables are the only
    available primitives. No arithmetic operation or hand-written block is
    supplied to the returned executable. Costs count each formula-tree node,
    treating each admitted binary interface as one node (not its expansion).
    """
    operators = {}
    for name, table in grammar.unary:
        operators[name] = (1, table)
    for name, table in grammar.binary:
        if name in operators:
            raise InvalidCertificate("duplicate primitive name")
        operators[name] = (2, table)
    for table in selected:
        if not isinstance(table, int) or not 0 <= table < 16:
            raise InvalidCertificate("invalid discovered binary table")
        name = f"u{table:02x}"
        if name in operators:
            raise InvalidCertificate("discovered macro shadows a primitive")
        operators[name] = (2, table)

    def interpret(expr, bits):
        if not expr.args:
            if expr.op not in ("x0", "x1", "x2"):
                raise InvalidCertificate(f"unknown input: {expr.op}")
            return bits[int(expr.op[1])], 0
        if expr.op not in operators:
            raise InvalidCertificate(f"unknown operation: {expr.op}")
        arity, table = operators[expr.op]
        if len(expr.args) != arity:
            raise InvalidCertificate("wrong operator arity")
        children = [interpret(arg, bits) for arg in expr.args]
        index = sum(value << i for i, (value, _cost) in enumerate(children))
        return (table >> index) & 1, 1 + sum(cost for _, cost in children)

    try:
        certificates = (programs[first_mask], programs[second_mask])
    except KeyError as exc:
        raise InvalidCertificate("required behaviour missing") from exc

    total_cost = sum(cost for cost, _expr in certificates)
    if total_cost > budget:
        raise BudgetExceeded(f"unpromoted cost {total_cost} exceeds {budget}")

    derived_masks = [0, 0]
    for row in range(8):
        bits = tuple((row >> i) & 1 for i in range(3))
        for i, ((declared_cost, expr), mask) in enumerate(
            zip(certificates, (first_mask, second_mask))
        ):
            value, actual_cost = interpret(expr, bits)
            if actual_cost != declared_cost:
                raise InvalidCertificate("certificate cost mismatch")
            if value != (mask >> row) & 1:
                raise InvalidCertificate("certificate truth table mismatch")
            derived_masks[i] |= value << row

    # The minimal future-relevant state is the checked behaviour, not the
    # interpreter's syntax tree. Derive the two masks from the *program*, not
    # by copying the verifier-supplied expected masks (an oracle leak).
    verified_first, verified_second = derived_masks

    def executable(first, second, third):
        bits = (first, second, third)
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("binary inputs required")
        row = first | (second << 1) | (third << 2)
        return (verified_first >> row) & 1, (verified_second >> row) & 1

    return executable
