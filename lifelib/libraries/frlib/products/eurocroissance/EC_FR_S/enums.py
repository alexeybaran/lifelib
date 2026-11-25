"""IntEnum families passed as cell arguments in EC_FR_S, stored with the model."""

from enum import IntEnum


class AcctTiming(IntEnum):
    BOM = 0
    AFT_LEVY = 1
    AFT_EXIT = 2
    AFT_PREM = 3
    AFT_STRIKE = 4
    AFT_RETURN = 5
    AFT_PERF = 6
    AFT_TOP_UP = 7


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
