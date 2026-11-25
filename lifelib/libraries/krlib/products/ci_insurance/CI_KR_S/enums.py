"""Label families passed as cell arguments in CI_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Cause(StrEnum):
    cancer = "cancer"
    ami = "ami"
    stroke = "stroke"
    other = "other"
    ltc = "ltc"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    CI = "CI"
    DEATH = "DEATH"
    DEATH_CI = "DEATH_CI"
    LAPSE = "LAPSE"
    LAPSE_CI = "LAPSE_CI"
