"""IntEnum families passed as cell arguments in CI_KR_S, stored with the model."""

from enum import IntEnum


class Cause(IntEnum):
    cancer = 0
    ami = 1
    stroke = 2
    other = 3
    ltc = 4


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    CI = 0
    DEATH = 1
    DEATH_CI = 2
    LAPSE = 3
    LAPSE_CI = 4
    ALL = 5
