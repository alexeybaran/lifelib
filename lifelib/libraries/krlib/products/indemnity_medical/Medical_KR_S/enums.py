"""Label families passed as cell arguments in Medical_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Stream(StrEnum):
    ge_in = "ge_in"
    ge_out = "ge_out"
    np_in = "np_in"
    np_room = "np_room"
    np_out = "np_out"
    physio = "physio"
    inject = "inject"
    mri = "mri"


class UtilColumn(StrEnum):
    adm_rate = "adm_rate"
    los_days = "los_days"
    visit_rate_ge = "visit_rate_ge"
    visit_rate_np = "visit_rate_np"
    act_rate_physio = "act_rate_physio"
    act_rate_inject = "act_rate_inject"
    act_rate_mri = "act_rate_mri"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    BEF_SUSPEND = "BEF_SUSPEND"
    BEF_RENEWAL = "BEF_RENEWAL"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    GE_IN = "GE_IN"
    GE_OUT = "GE_OUT"
    NP_IN = "NP_IN"
    NP_OUT = "NP_OUT"
    NP_THREE = "NP_THREE"
