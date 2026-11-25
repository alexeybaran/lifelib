"""IntEnum families passed as cell arguments in Sofort_DE_S, stored with the model."""

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
    U = 2


class Basis(IntEnum):
    FIRST = 0
    SECOND = 1


class AnnuityKind(IntEnum):
    ANNUITANT = 0
    SURVIVOR = 1
    ALL = 2


class ClaimKind(IntEnum):
    GUARANTEE = 0
    REFUND = 1
    ALL = 2
