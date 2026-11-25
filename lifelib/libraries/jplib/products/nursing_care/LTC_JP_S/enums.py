"""Label families passed as cell arguments in LTC_JP_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Grade(StrEnum):
    support1 = "support1"
    support2 = "support2"
    care1 = "care1"
    care2 = "care2"
    care3 = "care3"


class PrevParam(StrEnum):
    prev_ceil = "prev_ceil"
    prev_beta = "prev_beta"
    prev_x_mid = "prev_x_mid"
    prev_age_low = "prev_age_low"
    prev_rate_low = "prev_rate_low"
    prev_age_high = "prev_age_high"
    prev_rate_high = "prev_rate_high"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    LUMP = "LUMP"
    ANNUITY = "ANNUITY"
    DEMENTIA = "DEMENTIA"
    LAPSE = "LAPSE"
