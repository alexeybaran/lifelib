"""Label families passed as cell arguments in Cancer_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Tier(StrEnum):
    high = "high"
    general = "general"
    minor = "minor"
    similar = "similar"


class ShareColumn(StrEnum):
    minor_share = "minor_share"
    high_share = "high_share"
    similar_share = "similar_share"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    AFT_DECR = "AFT_DECR"
    BEF_LAPSE = "BEF_LAPSE"


class Kind(StrEnum):
    DIAG_GEN = "DIAG_GEN"
    DIAG_HIGH = "DIAG_HIGH"
    DIAG_MINOR = "DIAG_MINOR"
    DIAG_SIMILAR = "DIAG_SIMILAR"
    HOSP = "HOSP"
    SURGERY = "SURGERY"
    TREAT = "TREAT"
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
