"""Label families passed as cell arguments in Basis_DE_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_DEATH = "AFT_DEATH"
    AFT_FREEZE = "AFT_FREEZE"


class AvTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    AFT_PREM = "AFT_PREM"
    AFT_INT = "AFT_INT"


class Kind(StrEnum):
    DEATH = "DEATH"
    ANNUITY = "ANNUITY"
    SURVIVOR = "SURVIVOR"
