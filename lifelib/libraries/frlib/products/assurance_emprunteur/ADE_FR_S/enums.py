"""IntEnum families passed as cell arguments in ADE_FR_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DECR = 1


class Kind(IntEnum):
    DEATH = 0
    PTIA = 1
    ITT = 2
    IPT = 3
    LAPSE = 4
    MATURITY = 5
    ALL = 6
