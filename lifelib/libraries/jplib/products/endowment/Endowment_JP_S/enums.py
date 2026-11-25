"""Label families passed as cell arguments in Endowment_JP_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Sex(StrEnum):
    M = "M"
    F = "F"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    STAGED = "STAGED"
    MATURITY = "MATURITY"
    LAPSE = "LAPSE"
    PH_DEATH = "PH_DEATH"
