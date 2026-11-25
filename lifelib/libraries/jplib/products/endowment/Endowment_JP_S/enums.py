"""IntEnum families passed as cell arguments in Endowment_JP_S, stored with the model."""

from enum import IntEnum


class Sex(IntEnum):
    M = 0
    F = 1


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    STAGED = 1
    MATURITY = 2
    LAPSE = 3
    PH_DEATH = 4
    ALL = 5
