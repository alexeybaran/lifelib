"""Codes for Variable Universal Life claim types and account-value timing."""
from enum import IntEnum


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    WITHDRAWAL = 3
    ALL = 4


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_FEE = 2
    BEF_INV = 3
    BEF_ME = 4
    EOM = 5
