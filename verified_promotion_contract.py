"""Constitutional promotion contract earned from live verifier failures.

A candidate result may be promoted only if:
1. its verifier actually executed and passed;
2. the promoted scope is no broader than the verified scope, unless a named
   scope-widening/attachment certificate was independently verified;
3. symbolic inequalities are explicit/source-backed or forced by a verified
   property; distinct labels alone never witness inequality;
4. partial algebra contradictions were checked under equality completion when
   aliasing is semantically possible.

This module is process machinery, not mathematical evidence for E677=>E255.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PromotionEvidence:
    verifier_id: str
    executed: bool
    passed: bool
    verified_scope: frozenset[str]
    promoted_scope: frozenset[str]
    widening_certificate: str | None = None
    widening_certificate_passed: bool = False
    equality_completion_required: bool = False
    equality_completion_passed: bool = False
    inequalities: tuple[tuple[str,str,str], ...] = ()  # lhs,rhs,justification

class PromotionContractError(RuntimeError): pass

def check_promotion(e: PromotionEvidence) -> None:
    if not e.executed:
        raise PromotionContractError('verifier-not-executed')
    if not e.passed:
        raise PromotionContractError('verifier-not-passed')
    widening = e.promoted_scope - e.verified_scope
    if widening and not (e.widening_certificate and e.widening_certificate_passed):
        raise PromotionContractError('scope-widening-without-certificate:' + ','.join(sorted(widening)))
    if e.equality_completion_required and not e.equality_completion_passed:
        raise PromotionContractError('equality-completion-required')
    for a,b,why in e.inequalities:
        if not why.strip():
            raise PromotionContractError(f'unjustified-inequality:{a}!={b}')
        if why.strip().lower() in {'different names','distinct labels','syntactic inequality'}:
            raise PromotionContractError(f'syntactic-inequality-forbidden:{a}!={b}')

def promotable(e: PromotionEvidence) -> tuple[bool,str]:
    try:
        check_promotion(e); return True,'PASS'
    except PromotionContractError as ex:
        return False,str(ex)
