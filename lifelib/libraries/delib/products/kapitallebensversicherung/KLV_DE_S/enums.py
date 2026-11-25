"""IntEnum families passed as cell arguments in KLV_DE_S, stored with the model."""

from enum import IntEnum


class ResTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_INT = 2


class SurTiming(IntEnum):
    BEF_INT = 0
    AFT_INT = 1
    AFT_CREDIT = 2


class PolsTiming(IntEnum):
    BEF_DECR = 0
    AFT_MORT = 1
    AFT_LAPSE = 2


class Kind(IntEnum):
    DEATH = 0
    MATURITY = 1
    LAPSE = 2
    ALL = 3
