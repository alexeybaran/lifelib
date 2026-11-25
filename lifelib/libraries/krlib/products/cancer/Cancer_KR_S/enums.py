"""IntEnum families passed as cell arguments in Cancer_KR_S, stored with the model."""

from enum import IntEnum


class Tier(IntEnum):
    high = 0
    general = 1
    minor = 2
    similar = 3


class ShareColumn(IntEnum):
    minor_share = 0
    high_share = 1
    similar_share = 2


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DECR = 1
    BEF_LAPSE = 2


class Kind(IntEnum):
    DIAG_GEN = 0
    DIAG_HIGH = 1
    DIAG_MINOR = 2
    DIAG_SIMILAR = 3
    HOSP = 4
    SURGERY = 5
    TREAT = 6
    DEATH = 7
    LAPSE = 8
    MATURITY = 9
    ALL = 10
