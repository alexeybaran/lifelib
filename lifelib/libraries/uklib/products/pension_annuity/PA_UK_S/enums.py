"""IntEnum families passed as cell arguments in PA_UK_S, stored with the model."""

from enum import IntEnum


class AnnuityKind(IntEnum):
    ANNUITANT = 0
    ALL = 1


class Kind(IntEnum):
    VP = 0
    PROP = 1
    ALL = 2
