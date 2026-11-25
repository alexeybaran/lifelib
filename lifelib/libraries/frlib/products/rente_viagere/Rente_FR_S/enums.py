"""IntEnum families passed as cell arguments in Rente_FR_S, stored with the model."""

from enum import IntEnum


class Sex(IntEnum):
    M = 0
    F = 1
    mix = 2


class AnnuityKind(IntEnum):
    ANNUITANT = 0
    ALL = 1


class Kind(IntEnum):
    PRORATA = 0
    ALL = 1
