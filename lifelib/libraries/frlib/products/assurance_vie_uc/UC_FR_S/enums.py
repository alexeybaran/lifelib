"""IntEnum families passed as cell arguments in UC_FR_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    OPENING = 0
    BEF_FEE = 1
    BEF_WD = 2
    BEF_LEVY = 3
    BEF_DECR = 4


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ALL = 2
