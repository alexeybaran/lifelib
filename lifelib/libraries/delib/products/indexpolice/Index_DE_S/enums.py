"""Label families passed as cell arguments in Index_DE_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    AFT_PREM = "AFT_PREM"
    AFT_CHARGE = "AFT_CHARGE"
    AFT_GUAR = "AFT_GUAR"
    AFT_CREDIT = "AFT_CREDIT"


class PolsTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_DEATH = "AFT_DEATH"
    AFT_LAPSE = "AFT_LAPSE"


class ClaimKind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
