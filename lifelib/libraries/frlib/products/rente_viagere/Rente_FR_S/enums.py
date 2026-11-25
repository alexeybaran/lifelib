"""Label families passed as cell arguments in Rente_FR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Sex(StrEnum):
    M = "M"
    F = "F"
    mix = "mix"


class AnnuityKind(StrEnum):
    ANNUITANT = "ANNUITANT"
    ALL = "ALL"


class Kind(StrEnum):
    PRORATA = "PRORATA"
