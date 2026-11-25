"""IntEnum families passed as cell arguments in Euro_FR_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_WD = 2
    AFT_INT = 3


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ALL = 2
