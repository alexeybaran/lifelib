"""Label families passed as cell arguments in IP_UK_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    BENEFIT = "BENEFIT"
    DEATH = "DEATH"
    LAPSE = "LAPSE"
