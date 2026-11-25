"""IntEnum families passed as cell arguments in Pflege_DE_S, stored with the model."""

from enum import IntEnum


class Timing(IntEnum):
    BEG = 0
    END = 1


class Kind(IntEnum):
    ANNUITY = 0
    LAPSE = 1
    DEATH = 2
    ALL = 3
