"""IntEnum families passed as cell arguments in Medical_JP_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    HOSP = 0
    SURGERY = 1
    ADVANCED = 2
    LUMP = 3
    LAPSE = 4
    ALL = 5
