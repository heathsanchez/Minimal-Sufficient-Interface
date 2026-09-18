"""QCKN downstream adapters and developmental control.

The frozen Lean QCK v1 branch is the constitutional source. Modules here adapt
finite/discrete developmental experiments onto that vocabulary and keep policy
above the semantic layer.
"""

from .finite_adapter import (
    CertifiedSubstitution,
    NewContextDefect,
    OperationAssessment,
    assess_operation,
    defect_to_pair_residual,
    representation_from_interface,
)
from .outcomes import (
    CertificateInvalid,
    ImplementationMismatch,
    OutOfScope,
    RecoveryUnavailable,
    ReserveRequired,
    Unknown,
)

__all__ = [
    "CertifiedSubstitution",
    "NewContextDefect",
    "OperationAssessment",
    "assess_operation",
    "defect_to_pair_residual",
    "representation_from_interface",
    "ReserveRequired",
    "RecoveryUnavailable",
    "ImplementationMismatch",
    "CertificateInvalid",
    "OutOfScope",
    "Unknown",
]
