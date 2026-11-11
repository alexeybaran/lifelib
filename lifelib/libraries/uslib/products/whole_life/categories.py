"""Codes for Whole Life claim types and in-force timing."""
from enum import IntEnum


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3


class Timing(IntEnum):
    BEF_DECR = 0
    BEF_SURR = 1
    BEF_MAT = 2
    AFT_DECR = 3


class DividendOption(IntEnum):
    OTHER = -1
    PUA = 0
    REDUCE_PREM = 1
    CASH = 2
    ACCUM = 3
