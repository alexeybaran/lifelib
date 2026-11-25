"""IntEnum families passed as cell arguments in TD_FR_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    PTIA = 1
    LAPSE = 2
    ALL = 3
