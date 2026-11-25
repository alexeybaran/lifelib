"""Label families passed as cell arguments in PER_FR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    BEF_REBAL = "BEF_REBAL"
    BOM = "BOM"
    BEF_CHARGE = "BEF_CHARGE"
    EOM = "EOM"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_RELEASE = "BEF_RELEASE"
    BEF_TRANSFER = "BEF_TRANSFER"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    EARLY_RELEASE = "EARLY_RELEASE"
    TRANSFER = "TRANSFER"
    MATURITY = "MATURITY"
