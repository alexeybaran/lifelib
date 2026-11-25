"""IntEnum families passed as cell arguments in MYGA_US_S, stored with the model."""

from enum import IntEnum


class AvTiming(IntEnum):
    BEF_WD = 0
    BEF_INV = 1
    EOM = 2


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_MORT = 1
    BEF_LAPSE = 2
    AFT_DECR = 3


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ANNUITIZATION = 2
    MATURITY = 3
    ALL = 4


class RateColumn(IntEnum):
    mva_ref_yield = 0
    market_rate = 1
