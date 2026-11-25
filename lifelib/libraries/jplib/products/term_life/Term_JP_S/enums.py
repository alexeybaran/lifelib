"""IntEnum families passed as cell arguments in Term_JP_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    BEF_DECLINE = 2
    AFT_DECR = 3


class Kind(IntEnum):
    DEATH = 0
    LIVING_NEEDS = 1
    LAPSE = 2
    ALL = 3
