"""IntEnum families passed as cell arguments in FRV_DE_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_CHARGE = 0
    AFT_CHARGE = 1
    AFT_WD = 2
    BEF_DECR = 3


class PolsTiming(IntEnum):
    BEF_DECR = 0
    AFT_DEATH = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
