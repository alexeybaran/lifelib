"""Label families passed as cell arguments in Obseques_FR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class BenefitKind(StrEnum):
    ILL = "ILL"
    ACC = "ACC"
    DEATH = "DEATH"
    PAID_UP = "PAID_UP"


class Kind(StrEnum):
    DEATH = "DEATH"
    DEATH_PAID_UP = "DEATH_PAID_UP"
    LAPSE = "LAPSE"


class CrossoverBasis(StrEnum):
    ISSUE = "ISSUE"
    CURRENT = "CURRENT"
