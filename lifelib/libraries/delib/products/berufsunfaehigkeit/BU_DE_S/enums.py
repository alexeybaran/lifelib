"""IntEnum families passed as cell arguments in BU_DE_S, stored with the model."""

from enum import IntEnum


class Timing(IntEnum):
    BEG = 0
    END = 1


class Kind(IntEnum):
    BU_RENTE = 0
    REINTEGRATION = 1
    LAPSE = 2
    ALL = 3
