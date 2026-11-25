"""Label families passed as cell arguments in WholeLife_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_SURR = "BEF_SURR"
    BEF_MAT = "BEF_MAT"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
