"""Label families passed as cell arguments in EC_FR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AcctTiming(StrEnum):
    BOM = "BOM"
    AFT_LEVY = "AFT_LEVY"
    AFT_EXIT = "AFT_EXIT"
    AFT_PREM = "AFT_PREM"
    AFT_STRIKE = "AFT_STRIKE"
    AFT_RETURN = "AFT_RETURN"
    AFT_PERF = "AFT_PERF"
    AFT_TOP_UP = "AFT_TOP_UP"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
