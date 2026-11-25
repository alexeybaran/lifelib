"""Label families passed as cell arguments in ULB_UK_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    BEF_GROWTH = "BEF_GROWTH"
    AFT_GROWTH = "AFT_GROWTH"
    AFT_CHARGE = "AFT_CHARGE"
    AFT_WD = "AFT_WD"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_SURR = "BEF_SURR"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    SURRENDER = "SURRENDER"
