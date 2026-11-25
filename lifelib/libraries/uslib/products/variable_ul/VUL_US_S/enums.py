"""IntEnum families passed as cell arguments in VUL_US_S, stored with the model."""

from enum import IntEnum


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_FEE = 2
    BEF_INV = 3
    BEF_ME = 4
    EOM = 5


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
