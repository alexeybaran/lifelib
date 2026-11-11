"""Numeric names for deferred income annuity calculation categories."""

from enum import IntEnum


class Claim(IntEnum):
    INVALID = -1
    DEATH = 0
    REFUND = 1
    ALL = 2


class PaymentTiming(IntEnum):
    INVALID = -1
    arrears = 0
    advance = 1


class ReductionTrigger(IntEnum):
    INVALID = -1
    either = 0
    primary = 1


class MortalityBasis(IntEnum):
    INVALID = -1
    anchor = 0
    generational = 1


class FactorBasis(IntEnum):
    INVALID = -1
    table = 0
    formula = 1


class PayoutForm(IntEnum):
    INVALID = -1
    LO = 0
    CR = 1
    IR = 2
    PC = 3


class DeathBenefit(IntEnum):
    INVALID = -1
    NONE = 0
    ROP = 1
