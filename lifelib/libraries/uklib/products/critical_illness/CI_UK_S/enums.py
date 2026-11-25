"""IntEnum families passed as cell arguments in CI_UK_S, stored with the model."""

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


class Sex(IntEnum, metaclass=ByText):
    M = 0
    F = 1


class Smoker(IntEnum, metaclass=ByText):
    NS = 0
    S = 1


class RateColumn(IntEnum):
    i_ci = 0
    q_d = 1


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class BenefitKind(IntEnum):
    MAIN = 0
    AP = 1
    CHILD = 2


class Kind(IntEnum):
    MAIN = 0
    AP = 1
    CHILD = 2
    LAPSE = 3
    ALL = 4
