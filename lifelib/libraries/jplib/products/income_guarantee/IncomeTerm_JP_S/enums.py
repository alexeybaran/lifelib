"""IntEnum families passed as cell arguments in IncomeTerm_JP_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    ANNUITY = 0
    COMMUTATION = 1
    LIVING_NEEDS = 2
    LAPSE = 3
    ALL = 4
