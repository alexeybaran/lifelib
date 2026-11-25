"""Label families passed as cell arguments in ULSG_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Timing(StrEnum):
    BEF_PREM = "BEF_PREM"
    BEF_WD = "BEF_WD"
    BEF_FEE = "BEF_FEE"
    BEF_COI = "BEF_COI"
    BEF_INV = "BEF_INV"
    EOM = "EOM"


class LoanTiming(StrEnum):
    BEF_INT = "BEF_INT"


class PolTiming(StrEnum):
    BEF_MAT = "BEF_MAT"
    BEF_NB = "BEF_NB"
    BEF_DECR = "BEF_DECR"


class Claim(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    REFUND = "REFUND"
    WITHDRAWAL = "WITHDRAWAL"
    GRACE = "GRACE"
    MATURITY = "MATURITY"
