"""Label families passed as cell arguments in UC_FR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AvTiming(StrEnum):
    OPENING = "OPENING"
    BEF_FEE = "BEF_FEE"
    BEF_WD = "BEF_WD"
    BEF_LEVY = "BEF_LEVY"
    BEF_DECR = "BEF_DECR"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
