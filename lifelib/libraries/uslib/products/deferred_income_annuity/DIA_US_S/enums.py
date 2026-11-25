"""IntEnum families passed as cell arguments in DIA_US_S, stored with the model."""

from enum import IntEnum


class Claim(IntEnum):
    DEATH = 0
    REFUND = 1
    ALL = 2
