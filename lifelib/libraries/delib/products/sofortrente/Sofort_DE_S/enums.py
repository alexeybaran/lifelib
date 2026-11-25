"""IntEnum families passed as cell arguments in Sofort_DE_S, stored with the model."""

from enum import IntEnum


class Sex(IntEnum):
    M = 0
    F = 1
    U = 2


class Basis(IntEnum):
    FIRST = 0
    SECOND = 1


class AnnuityKind(IntEnum):
    ANNUITANT = 0
    SURVIVOR = 1
    ALL = 2


class ClaimKind(IntEnum):
    GUARANTEE = 0
    REFUND = 1
    ALL = 2
