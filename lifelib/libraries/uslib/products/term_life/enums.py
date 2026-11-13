"""Category values used by the Term_US_S saved model."""

from enum import IntEnum


class Plan(IntEnum):
    T10 = 10
    T20 = 20
    T30 = 30


class Sex(IntEnum):
    M = 0
    F = 1


class RateClass(IntEnum):
    PPlusNT = 0
    PNT = 1
    StdNT = 2
    StdTob = 3
