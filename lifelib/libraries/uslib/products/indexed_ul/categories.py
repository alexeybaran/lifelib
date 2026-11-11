"""Codes for Indexed Universal Life claim types and account-value timing."""
from enum import IntEnum


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    WITHDRAWAL = 3
    ALL = 4


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_CREDIT = 1
    BEF_WD = 2
    BEF_FEE = 3
    BEF_SWEEP = 4
    BEF_INV = 5
    EOM = 6
