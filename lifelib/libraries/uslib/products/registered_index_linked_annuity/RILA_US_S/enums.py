"""Label families passed as cell arguments in RILA_US_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Claim(StrEnum):
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"


class MarketField(StrEnum):
    index_level = "index_level"
    mvr = "mvr"
    risk_free = "risk_free"
    div_yield = "div_yield"
    impl_vol = "impl_vol"


class OptionLeg(StrEnum):
    ATM_CALL = "ATM_CALL"
    OTM_CALL = "OTM_CALL"
    OTM_PUT = "OTM_PUT"
    ATM_PUT = "ATM_PUT"
    FLOOR_PUT = "FLOOR_PUT"
    STEP_BINARY = "STEP_BINARY"
    EDGE_BINARY = "EDGE_BINARY"


class MarketQuote(StrEnum):
    CURRENT = "CURRENT"
    TERM_START = "TERM_START"


class Timing(StrEnum):
    BEF_CREDIT = "BEF_CREDIT"
    BEF_ROLL = "BEF_ROLL"
    BEF_WD = "BEF_WD"
    AFT_WD = "AFT_WD"
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    BEF_TERM_SURR = "BEF_TERM_SURR"
    AFT_DECR = "AFT_DECR"


class Bucket(StrEnum):
    OPTION = "OPTION"
    FIXED = "FIXED"
    HOLDING = "HOLDING"


class CreditType(StrEnum):
    CAP = "CAP"
    STEP = "STEP"
    EDGE = "EDGE"
    FLOOR = "FLOOR"
