"""IntEnum families passed as cell arguments in Basis_DE_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DEATH = 1
    AFT_FREEZE = 2


class AvTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_INT = 2


class Kind(IntEnum):
    DEATH = 0
    ANNUITY = 1
    SURVIVOR = 2
    ALL = 3
