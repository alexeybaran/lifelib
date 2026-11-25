"""IntEnum families passed as cell arguments in WholeLife_KR_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    REDUCTION = 2
    ALL = 3
