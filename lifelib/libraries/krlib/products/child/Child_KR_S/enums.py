"""IntEnum families passed as cell arguments in Child_KR_S, stored with the model."""

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


class LapseColumn(IntEnum):
    first_year_rate = 0
    completion_rate = 1
    ultimate_rate = 2


class Cover(IntEnum):
    disability = 0
    disease_disab = 1
    cancer = 2
    minor_cancer = 3
    cerebral = 4
    cardiac = 5
    surgery = 6
    fracture = 7
    burn = 8
    hosp_acc = 9
    hosp_dis = 10
    liability = 11
    neonatal = 12


class Kind(IntEnum):
    DISABILITY = 0
    DIAGNOSIS = 1
    SURGERY = 2
    HOSPITAL = 3
    EVENT = 4
    LIABILITY = 5
    NEONATAL = 6
    DEATH = 7
    LAPSE = 8
    MATURITY = 9
    VOID = 10
    ALL = 11


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class NeoTiming(IntEnum):
    birth = 0
    block = 1


class BasisParam(IntEnum, metaclass=ByText):
    disab_severity = 0
    disease_disab_severity = 1
    surgery_rate_cancer = 2
    surgery_rate_cerebral = 3
    surgery_rate_cardiac = 4
    liability_severity = 5
    hosp_cap_factor = 6
    waiver_disab_share = 7
    payer_disab_ratio = 8
    leak_share = 9
    void_rate_ann = 10
    broad_def_factor = 11
    net_prem_ratio = 12
