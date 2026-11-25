"""IntEnum families passed as cell arguments in WholeLife_JP_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    BEF_SPIKE = 2
    AFT_DECR = 3


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ALL = 2
