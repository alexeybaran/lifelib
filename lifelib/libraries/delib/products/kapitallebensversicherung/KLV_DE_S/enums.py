"""Label families passed as cell arguments in KLV_DE_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class ResTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    AFT_PREM = "AFT_PREM"
    AFT_INT = "AFT_INT"


class SurTiming(StrEnum):
    BEF_INT = "BEF_INT"
    AFT_INT = "AFT_INT"
    AFT_CREDIT = "AFT_CREDIT"


class PolsTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_MORT = "AFT_MORT"
    AFT_LAPSE = "AFT_LAPSE"


class Kind(StrEnum):
    DEATH = "DEATH"
    MATURITY = "MATURITY"
    LAPSE = "LAPSE"
