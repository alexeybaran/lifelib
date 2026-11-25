"""IntEnum families passed as cell arguments in VA_KR_S, stored with the model."""

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


class FundTiming(IntEnum):
    BEF_PREM = 0
    BEF_DEDUCT = 1
    AFT_DEDUCT = 2
    AFT_DERISK = 3


class PolTiming(IntEnum):
    BEF_DECR = 0
    BEF_LAPSE = 1
    AFT_DECR = 2


class Kind(IntEnum):
    DEATH = 0
    LAPSE = 1
    ANNUITY = 2
    MATURITY = 3
    ALL = 4


class ChargeLine(IntEnum, metaclass=ByText):
    acq_charge = 0
    maint_charge_in = 1
    maint_charge_after = 2
    other_charge = 3
    gmdb_charge = 4
    gmab_charge_asset = 5
    gmab_charge_prem = 6
    surr_charge = 7
    surr_charge_cap = 8
    annuity_charge = 9
    fund_expense = 10
    comm_yr1 = 11
    comm_yr2 = 12
    comm_yr3 = 13
    comm_yr4 = 14
    comm_yr5 = 15
    expense_acq = 16
    expense_maint = 17
