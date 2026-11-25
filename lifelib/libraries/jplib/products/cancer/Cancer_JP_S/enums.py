"""IntEnum families passed as cell arguments in Cancer_JP_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DIAG = 0
    INSITU = 1
    HOSP = 2
    SURGERY = 3
    TREAT = 4
    OUTPATIENT = 5
    ADVANCED = 6
    DISCHARGE = 7
    LAPSE = 8
    ALL = 9
