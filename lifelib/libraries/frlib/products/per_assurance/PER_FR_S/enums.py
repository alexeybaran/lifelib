"""IntEnum families passed as cell arguments in PER_FR_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_REBAL = 0
    BOM = 1
    BEF_CHARGE = 2
    EOM = 3


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_RELEASE = 1
    BEF_TRANSFER = 2
    AFT_DECR = 3


class Kind(IntEnum):
    DEATH = 0
    EARLY_RELEASE = 1
    TRANSFER = 2
    MATURITY = 3
    ALL = 4
