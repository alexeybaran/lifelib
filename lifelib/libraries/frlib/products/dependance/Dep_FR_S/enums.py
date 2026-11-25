"""Label families passed as cell arguments in Dep_FR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Cause(StrEnum):
    accident = "accident"
    illness = "illness"
    neuro = "neuro"


class PrevParam(StrEnum):
    prev_ceil = "prev_ceil"
    prev_beta = "prev_beta"
    prev_x_mid = "prev_x_mid"


class Severity(StrEnum):
    partial = "partial"
    total = "total"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    RENTE = "RENTE"
    CAPITAL = "CAPITAL"
    LAPSE = "LAPSE"
