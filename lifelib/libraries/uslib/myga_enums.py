"""Public MYGA categories retained from the adjusted model."""
from enum import IntEnum

class Sex(IntEnum):
    M = 0
    F = 1

class Renewal(IntEnum):
    ROLLOVER = 0
    ANNUAL_REDECLARE = 1

class FloorWithdrawal(IntEnum):
    GROSS = 0
    NET_OF_CHARGES = 1

class FreeWithdrawal(IntEnum):
    PCT_AV = 0
    INTEREST_ONLY = 1

class MVAFamily(IntEnum):
    LINEAR_DURATION = 0
    GEOMETRIC = 1
    DECLARED_DIFFERENTIAL = 2

class MVACap(IntEnum):
    NONE = 0
    SYM_SC = 1
    MIN_SC_INTEREST = 2
    ASYM_SC_SNFL = 3
    GMIR_FLOOR = 4

class ChargeSchedule(IntEnum):
    NONE = 0
    INITIAL = 1
    RENEWAL = 2

class AccountTiming(IntEnum):
    BEF_WD = 0
    BEF_INV = 1
    EOM = 2

class CountTiming(IntEnum):
    BEF_DECR = 0
    BEF_MORT = 1
    BEF_LAPSE = 2
    AFT_DECR = 3

class Claim(IntEnum):
    TOTAL = 0
    DEATH = 1
    LAPSE = 2
    ANNUITIZATION = 3
    MATURITY = 4
