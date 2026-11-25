"""Label families passed as cell arguments in VA_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class RateColumn(StrEnum):
    vix_sq = "vix_sq"
    cmt10 = "cmt10"


class Timing(StrEnum):
    BEF_PREM = "BEF_PREM"
    BEF_WD = "BEF_WD"
    BEF_INV = "BEF_INV"
    BEF_FEE = "BEF_FEE"
    BEF_ANNIV = "BEF_ANNIV"
    EOM = "EOM"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Claim(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
