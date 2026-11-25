"""Label families passed as cell arguments in MYGA_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    BEF_WD = "BEF_WD"
    BEF_INV = "BEF_INV"
    EOM = "EOM"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_MORT = "BEF_MORT"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    ANNUITIZATION = "ANNUITIZATION"
    MATURITY = "MATURITY"


class RateColumn(StrEnum):
    mva_ref_yield = "mva_ref_yield"
    market_rate = "market_rate"
