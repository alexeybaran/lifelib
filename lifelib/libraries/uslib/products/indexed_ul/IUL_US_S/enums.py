"""IntEnum families passed as cell arguments in IUL_US_S, stored with the model."""

from enum import IntEnum


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_CREDIT = 1
    BEF_WD = 2
    BEF_FEE = 3
    BEF_SWEEP = 4
    BEF_INV = 5
    EOM = 6


class PolTiming(IntEnum):
    BEF_MAT = 0
    BEF_NB = 1
    BEF_DECR = 2


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    WITHDRAWAL = 2
    MATURITY = 3
    ALL = 4
