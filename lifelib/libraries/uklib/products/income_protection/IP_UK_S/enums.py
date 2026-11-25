"""IntEnum families passed as cell arguments in IP_UK_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DECR = 1


class Kind(IntEnum):
    BENEFIT = 0
    DEATH = 1
    LAPSE = 2
    ALL = 3
