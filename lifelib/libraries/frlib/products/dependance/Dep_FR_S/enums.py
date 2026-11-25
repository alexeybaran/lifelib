"""IntEnum families passed as cell arguments in Dep_FR_S, stored with the model."""

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


class Cause(IntEnum, metaclass=ByText):
    accident = 0
    illness = 1
    neuro = 2


class PrevParam(IntEnum):
    prev_ceil = 0
    prev_beta = 1
    prev_x_mid = 2


class Severity(IntEnum):
    partial = 0
    total = 1


class PolTiming(IntEnum):
    BEF_DECR = 0
    AFT_DECR = 1


class Kind(IntEnum):
    RENTE = 0
    CAPITAL = 1
    LAPSE = 2
    ALL = 3
