"""IntEnum families passed as cell arguments in LTC_KR_S, stored with the model."""

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
    g1 = 0
    g2 = 1
    g3 = 2
    g4 = 3
    g5 = 4
    g6 = 5


class LapseParam(IntEnum):
    lapse_year1 = 0
    lapse_completion = 1
    lapse_ultimate = 2
    lapse_level_std = 3


class PrevParam(IntEnum):
    prev_ceil = 0
    prev_beta = 1
    prev_x_mid = 2
    prev_obs_67 = 3
    prev_obs_72 = 4
    prev_obs_77 = 5
    prev_obs_82 = 6
    prev_obs_88 = 7


class DemParam(IntEnum):
    dem_ceil = 0
    dem_beta = 1
    dem_x_mid = 2
    dem_factor_m = 3
    dem_factor_f = 4
    dem_obs_67 = 5
    dem_obs_72 = 6
    dem_obs_77 = 7
    dem_obs_82 = 8
    dem_obs_88 = 9


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    LUMP = 0
    ANNUITY = 1
    DEMENTIA = 2
    DEATH = 3
    LAPSE = 4
    VOID = 5
    MATURITY = 6
    ALL = 7
