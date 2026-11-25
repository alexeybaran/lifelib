"""IntEnum families passed as cell arguments in FIA_US_S, stored with the model."""

from enum import EnumType, IntEnum


class Text(str):
    """A label that is not a member: upstream's text, which also reads as ``.name``."""

    @property
    def name(self):
        return str(self)


class ByText(EnumType):
    """``Family[text]`` of a text that is not a member gives the text itself.

    A family the formulas look up by text (a label read from data or built from text)
    uses this: an unknown label then takes upstream's path, to upstream's own check
    (``raise ValueError("invalid credit_method")``) or upstream's failed table lookup.
    """

    def __getitem__(cls, text):
        member = cls._member_map_.get(text)
        if member is not None:
            return member
        return Text(text) if isinstance(text, str) else text


class GlwbBasis(IntEnum, metaclass=ByText):
    single = 0
    joint = 1


class CreditMethod(IntEnum, metaclass=ByText):
    cap = 0
    par = 1
    par_cap = 2
    spread = 3
    trigger = 4


class ScenarioField(IntEnum):
    index_level = 0
    mva_ref_yield = 1


class Timing(IntEnum):
    BEF_PREM = 0
    BEF_INV = 1
    BEF_FEE = 2
    BEF_ROLLUP = 3
    BEF_STEP_UP = 4
    BEF_WD = 5
    EOY = 6


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_MORT = 1
    BEF_LAPSE = 2
    AFT_DECR = 3


class Claim(IntEnum):
    DEATH = 0
    LAPSE = 1
    MATURITY = 2
    ALL = 3
