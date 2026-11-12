"""Codes for Universal Life claim types and account-value timing."""
from enum import IntEnum


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_FEE = 2
    BEF_INV = 3
    EOM = 4


class DeathBenefitOption(IntEnum):
    OTHER = -1
    A = 0
    B = 1


class Qualification(IntEnum):
    OTHER = -1
    GPT = 0
    CVAT = 1


class PremiumType(IntEnum):
    OTHER = -1
    SINGLE = 0
    LEVEL = 1
    TARGET = 2
