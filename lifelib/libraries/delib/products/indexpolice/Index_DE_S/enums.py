"""IntEnum families passed as cell arguments in Index_DE_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1
    AFT_CHARGE = 2
    AFT_GUAR = 3
    AFT_CREDIT = 4


class PolsTiming(IntEnum):
    BEF_DECR = 0
    AFT_DEATH = 1
    AFT_LAPSE = 2


class ClaimKind(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
