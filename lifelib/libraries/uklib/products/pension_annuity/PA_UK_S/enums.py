"""Label families passed as cell arguments in PA_UK_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AnnuityKind(StrEnum):
    ANNUITANT = "ANNUITANT"
    ALL = "ALL"


class Kind(StrEnum):
    VP = "VP"
    PROP = "PROP"
