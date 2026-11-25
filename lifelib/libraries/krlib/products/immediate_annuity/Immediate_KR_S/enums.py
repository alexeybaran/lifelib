"""Label families passed as cell arguments in Immediate_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
