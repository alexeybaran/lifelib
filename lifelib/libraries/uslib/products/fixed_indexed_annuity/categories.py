"""Codes for Fixed Indexed Annuity claim types."""
from enum import IntEnum


class Claim(IntEnum):
    INVALID = -1
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
