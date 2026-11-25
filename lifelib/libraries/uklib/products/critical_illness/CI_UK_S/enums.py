"""IntEnum families passed as cell arguments in CI_UK_S, stored with the model."""

from enum import IntEnum


class Sex(IntEnum):
    M = 0
    F = 1


class Smoker(IntEnum):
    NS = 0
    S = 1


class RateColumn(IntEnum):
    i_ci = 0
    q_d = 1


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class BenefitKind(IntEnum):
    MAIN = 0
    AP = 1
    CHILD = 2


class Kind(IntEnum):
    MAIN = 0
    AP = 1
    CHILD = 2
    LAPSE = 3
    ALL = 4
