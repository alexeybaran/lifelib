"""IntEnum families passed as cell arguments in ULB_UK_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_GROWTH = 0
    AFT_GROWTH = 1
    AFT_CHARGE = 2
    AFT_WD = 3


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_SURR = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    SURRENDER = 1
    ALL = 2
