"""IntEnum families passed as cell arguments in RV_DE_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_INT = 2


class PolsTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class ClaimKind(IntEnum):
    DEATH = 0
    LAPSE = 1
    COMMUTATION = 2
    ALL = 3
