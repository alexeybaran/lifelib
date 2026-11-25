"""IntEnum families passed as cell arguments in ULSG_US_S, stored with the model."""

from enum import IntEnum


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_FEE = 2
    BEF_COI = 3
    BEF_INV = 4
    EOM = 5


class LoanTiming(IntEnum):
    BEF_INT = 0


class PolTiming(IntEnum):
    BEF_MAT = 0
    BEF_NB = 1
    BEF_DECR = 2


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    REFUND = 2
    WITHDRAWAL = 3
    GRACE = 4
    MATURITY = 5
    ALL = 6
