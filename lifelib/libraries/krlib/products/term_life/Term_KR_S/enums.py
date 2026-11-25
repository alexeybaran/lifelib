"""IntEnum families passed as cell arguments in Term_KR_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    BEF_DECLINE = 2
    AFT_DECR = 3


class Kind(IntEnum):
    DEATH = 0
    ACC_DEATH = 1
    ACCEL = 2
    MATURITY = 3
    LAPSE = 4
    ALL = 5
