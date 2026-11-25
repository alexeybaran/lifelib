"""IntEnum families passed as cell arguments in WOL_UK_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class BenefitKind(IntEnum):
    NON_ACC = 0
    ACC = 1
    DEATH = 2
    PAID_UP = 3


class Kind(IntEnum):
    DEATH = 0
    DEATH_PU = 1
    LAPSE = 2
    ALL = 3
