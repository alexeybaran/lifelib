"""Label families passed as cell arguments in Sofort_DE_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Sex(StrEnum):
    M = "M"
    F = "F"
    U = "U"


class Basis(StrEnum):
    FIRST = "FIRST"
    SECOND = "SECOND"


class AnnuityKind(StrEnum):
    ANNUITANT = "ANNUITANT"
    SURVIVOR = "SURVIVOR"


class ClaimKind(StrEnum):
    GUARANTEE = "GUARANTEE"
    REFUND = "REFUND"
