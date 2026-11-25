"""IntEnum families passed as cell arguments in RLV_DE_S, stored with the model."""

from enum import IntEnum


class Sex(IntEnum):
    M = 0
    F = 1


class Smoker(IntEnum):
    N = 0
    R = 1


class ResTiming(IntEnum):
    BEF_PREM = 0
    AFT_PREM = 1


class PolsTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class ClaimKind(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
