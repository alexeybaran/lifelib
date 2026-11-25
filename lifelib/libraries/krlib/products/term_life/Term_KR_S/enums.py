"""Label families passed as cell arguments in Term_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    BEF_DECLINE = "BEF_DECLINE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    ACC_DEATH = "ACC_DEATH"
    ACCEL = "ACCEL"
    MATURITY = "MATURITY"
    LAPSE = "LAPSE"
