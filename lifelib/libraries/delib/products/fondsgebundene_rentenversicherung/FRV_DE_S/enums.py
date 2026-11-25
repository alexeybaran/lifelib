"""Label families passed as cell arguments in FRV_DE_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    BEF_CHARGE = "BEF_CHARGE"
    AFT_CHARGE = "AFT_CHARGE"
    AFT_WD = "AFT_WD"
    BEF_DECR = "BEF_DECR"


class PolsTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_DEATH = "AFT_DEATH"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
