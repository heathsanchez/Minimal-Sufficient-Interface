from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Sequence

from .continuation import Continuation
from .interface import CompiledInterface, compile_interface


@dataclass(frozen=True, order=True)
class LeanState:
    """Frozen semantic carrier for the first Lean-facing MSI experiment.

    The names are fixtures for the host domain, not MSI primitives.  The
    interface compiler sees only continuation outcomes.
    """

    tag: str
    payload: Hashable | None = None


SORT0 = LeanState("sort", 0)
SORT1 = LeanState("sort", 1)
SORT2 = LeanState("sort", 2)
PI = LeanState("pi")
RIGID = LeanState("rigid")
THUNK = LeanState("thunk")
LEAN_STATES = (SORT0, SORT1, SORT2, PI, RIGID, THUNK)


def _generic_sort_level(state: LeanState):
    return state.payload if state.tag == "sort" else None


def lean_continuations() -> tuple[Continuation, ...]:
    """Protected futures matching the first measured Sort/app/let lane.

    Outcome labels are intentionally operational and can be independently
    relabelled without changing the induced quotient.
    """

    return (
        Continuation(
            "expects_sort",
            lambda s: ("sort", _generic_sort_level(s)) if s.tag == "sort" else ("fallback",),
        ),
        Continuation(
            "app_expected_sort_0",
            lambda s: "direct" if _generic_sort_level(s) == 0 else "fallback",
        ),
        Continuation(
            "app_expected_sort_1",
            lambda s: "direct" if _generic_sort_level(s) == 1 else "fallback",
        ),
        Continuation(
            "let_expected_sort_2",
            lambda s: "direct" if _generic_sort_level(s) == 2 else "fallback",
        ),
    )


def compile_lean_sort_interface() -> CompiledInterface:
    return compile_interface("lean-sort-interface-v0", LEAN_STATES, lean_continuations())


def generic_decision(state: LeanState, consumer: str) -> tuple[str, Hashable | None]:
    """Reference decision made by consumer-side semantic rediscovery."""
    level = _generic_sort_level(state)
    if consumer == "expects_sort":
        return ("direct", level) if level is not None else ("fallback", None)
    if consumer.startswith("app_expected_sort_"):
        expected = int(consumer.rsplit("_", 1)[1])
        return ("direct", level) if level == expected else ("fallback", None)
    if consumer.startswith("let_expected_sort_"):
        expected = int(consumer.rsplit("_", 1)[1])
        return ("direct", level) if level == expected else ("fallback", None)
    raise KeyError(consumer)


def compiled_decision(
    interface: CompiledInterface,
    state: LeanState,
    consumer: str,
) -> tuple[str, Hashable | None]:
    """Decision through the compiled quotient class, without re-inspecting state."""
    cls = interface.ref(state)
    representatives = {}
    for candidate in LEAN_STATES:
        representatives.setdefault(interface.ref(candidate), candidate)
    return generic_decision(representatives[cls], consumer)


def rediscovery_workload(states: Sequence[LeanState], consumers: Sequence[str]) -> tuple[int, int, int]:
    """Count semantic classifications in LOCAL, SHARED and ABLATE arms.

    This is an operation-count falsifier, not a wall-clock performance claim.
    LOCAL reclassifies at each consumer. SHARED classifies once per produced
    value and reuses the interface. ABLATE pays for the shared classification
    but ignores it and repeats local rediscovery.
    """
    local = len(states) * len(consumers)
    shared = len(states)
    ablate = shared + local
    return local, shared, ablate
