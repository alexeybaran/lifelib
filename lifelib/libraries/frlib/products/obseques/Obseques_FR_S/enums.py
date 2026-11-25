"""IntEnum families passed as cell arguments in Obseques_FR_S, stored with the model."""

from enum import IntEnum


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class BenefitKind(IntEnum):
    ILL = 0
    ACC = 1
    DEATH = 2
    PAID_UP = 3


class Kind(IntEnum):
    DEATH = 0
    DEATH_PAID_UP = 1
    LAPSE = 2
    ALL = 3


class CrossoverBasis(IntEnum):
    ISSUE = 0
    CURRENT = 1
