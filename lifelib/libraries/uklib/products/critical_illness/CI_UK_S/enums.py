"""Label families passed as cell arguments in CI_UK_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Sex(StrEnum):
    M = "M"
    F = "F"


class Smoker(StrEnum):
    NS = "NS"
    S = "S"


class RateColumn(StrEnum):
    i_ci = "i_ci"
    q_d = "q_d"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class BenefitKind(StrEnum):
    MAIN = "MAIN"
    AP = "AP"
    CHILD = "CHILD"


class Kind(StrEnum):
    MAIN = "MAIN"
    AP = "AP"
    CHILD = "CHILD"
    LAPSE = "LAPSE"
