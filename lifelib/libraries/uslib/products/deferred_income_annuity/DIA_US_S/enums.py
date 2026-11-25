"""Label families passed as cell arguments in DIA_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Claim(StrEnum):
    DEATH = "DEATH"
    REFUND = "REFUND"
