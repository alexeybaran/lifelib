"""Label families passed as cell arguments in WP_UK_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class AsTiming(StrEnum):
    BEF_PREM = "BEF_PREM"
    BEF_RETURN = "BEF_RETURN"
    AFT_RETURN = "AFT_RETURN"
    AFT_CHARGE = "AFT_CHARGE"
    AFT_ST = "AFT_ST"
    AFT_MC = "AFT_MC"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_SURR = "BEF_SURR"
    AFT_DECR = "AFT_DECR"


class ClaimKind(StrEnum):
    DEATH = "DEATH"
    SURRENDER = "SURRENDER"
    GUARANTEE = "GUARANTEE"
    MATURITY = "MATURITY"


class Kind(StrEnum):
    DEATH = "DEATH"
    SURRENDER = "SURRENDER"
    MATURITY = "MATURITY"
