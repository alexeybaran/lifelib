"""IntEnum families passed as cell arguments in LTC_JP_S, stored with the model."""

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


class Grade(IntEnum, metaclass=ByText):
    support1 = 0
    support2 = 1
    care1 = 2
    care2 = 3
    care3 = 4


class PrevParam(IntEnum):
    prev_ceil = 0
    prev_beta = 1
    prev_x_mid = 2
    prev_age_low = 3
    prev_rate_low = 4
    prev_age_high = 5
    prev_rate_high = 6


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    LUMP = 0
    ANNUITY = 1
    DEMENTIA = 2
    LAPSE = 3
    ALL = 4
