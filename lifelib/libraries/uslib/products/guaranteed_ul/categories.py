"""Codes for ULSG timing, claims and premium categories."""
from enum import IntEnum


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_FEE = 2
    BEF_COI = 3
    BEF_INV = 4
    EOM = 5
    BEF_INT = 6
    BEF_MAT = 7
    BEF_NB = 8
    BEF_DECR = 9


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    REFUND = 2
    GRACE = 3
    WITHDRAWAL = 4
    MATURITY = 5
    ALL = 6


class PremiumType(IntEnum):
    UNKNOWN = -1
    LEVEL = 0
    SINGLE = 1
    TEN_PAY = 2


class PremiumMode(IntEnum):
    UNKNOWN = -1
    A = 0
    S = 1
    Q = 2
    M = 3
