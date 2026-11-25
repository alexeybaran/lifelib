"""Label families passed as cell arguments in RV_DE_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    AFT_PREM = "AFT_PREM"
    AFT_INT = "AFT_INT"


class PolsTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class ClaimKind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    COMMUTATION = "COMMUTATION"
