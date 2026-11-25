"""IntEnum families passed as cell arguments in Dep_FR_S, stored with the model."""

from enum import IntEnum


class Cause(IntEnum):
    accident = 0
    illness = 1
    neuro = 2


class PrevParam(IntEnum):
    prev_ceil = 0
    prev_beta = 1
    prev_x_mid = 2


class Severity(IntEnum):
    partial = 0
    total = 1


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DECR = 1


class Kind(IntEnum):
    RENTE = 0
    CAPITAL = 1
    LAPSE = 2
    ALL = 3
