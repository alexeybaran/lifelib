"""IntEnum families passed as cell arguments in Riester_DE_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DECR = 1


class AvTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_INT = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    TRANSFER = 2
    LUMPSUM = 3
    COMMUTATION = 4
    ANNUITY = 5
    ALL = 6
