"""Label families passed as cell arguments in IncomeTerm_JP_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    ANNUITY = "ANNUITY"
    COMMUTATION = "COMMUTATION"
    LIVING_NEEDS = "LIVING_NEEDS"
    LAPSE = "LAPSE"
