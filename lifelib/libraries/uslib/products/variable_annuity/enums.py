"""Category values used by the VA_US_S saved model."""

from enum import IntEnum


class StepupBasis(IntEnum):
    annual_CV = 0
    highest_quarterly_CV = 1

class GmdbOption(IntEnum):
    rollup = 0
    HQAV = 1
    basic = 2

class FeeResetRule(IntEnum):
    none = 0
    quinquennial = 1
    vix = 2

class RollupRule(IntEnum):
    fixed = 0
    cmt_linked = 1

class AvTiming(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_INV = 2
    BEF_FEE = 3
    EOM = 4

class BenefitTiming(IntEnum):
    BEF_PREM = 0
    BEF_WD = 1
    BEF_ANNIV = 2

class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2

class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
