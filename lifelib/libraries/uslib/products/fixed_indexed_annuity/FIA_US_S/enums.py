"""Label families passed as cell arguments in FIA_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class GlwbBasis(StrEnum):
    single = "single"
    joint = "joint"


class CreditMethod(StrEnum):
    cap = "cap"
    par = "par"
    par_cap = "par_cap"
    spread = "spread"
    trigger = "trigger"


class ScenarioField(StrEnum):
    index_level = "index_level"
    mva_ref_yield = "mva_ref_yield"


class Timing(StrEnum):
    BEF_PREM = "BEF_PREM"
    BEF_INV = "BEF_INV"
    BEF_FEE = "BEF_FEE"
    BEF_ROLLUP = "BEF_ROLLUP"
    BEF_STEP_UP = "BEF_STEP_UP"
    BEF_WD = "BEF_WD"
    EOY = "EOY"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_MORT = "BEF_MORT"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Claim(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
