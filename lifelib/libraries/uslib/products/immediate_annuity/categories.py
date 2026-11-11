"""Numeric names for the immediate annuity's calculation categories."""

from enum import IntEnum


class Claim(IntEnum):
    INVALID = -1
    REFUND = 0
    ALL = 1


class DiscountConvention(IntEnum):
    INVALID = -1
    COMPOUND = 0
    SIMPLE = 1


class PayoutForm(IntEnum):
    INVALID = -1
    life_only = 0
    life_certain = 1
    cash_refund = 2
    installment_refund = 3
    certain_only = 4


class ReductionTrigger(IntEnum):
    INVALID = -1
    either = 0
    primary = 1


class PaymentTiming(IntEnum):
    INVALID = -1
    arrears = 0
    advance = 1


class MortalityBasis(IntEnum):
    INVALID = -1
    table = 0
    scenario = 1
