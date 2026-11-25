"""Label families passed as cell arguments in LTC_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Grade(StrEnum):
    g1 = "g1"
    g2 = "g2"
    g3 = "g3"
    g4 = "g4"
    g5 = "g5"
    g6 = "g6"


class LapseParam(StrEnum):
    lapse_year1 = "lapse_year1"
    lapse_completion = "lapse_completion"
    lapse_ultimate = "lapse_ultimate"
    lapse_level_std = "lapse_level_std"


class PrevParam(StrEnum):
    prev_ceil = "prev_ceil"
    prev_beta = "prev_beta"
    prev_x_mid = "prev_x_mid"
    prev_obs_67 = "prev_obs_67"
    prev_obs_72 = "prev_obs_72"
    prev_obs_77 = "prev_obs_77"
    prev_obs_82 = "prev_obs_82"
    prev_obs_88 = "prev_obs_88"


class DemParam(StrEnum):
    dem_ceil = "dem_ceil"
    dem_beta = "dem_beta"
    dem_x_mid = "dem_x_mid"
    dem_factor_m = "dem_factor_m"
    dem_factor_f = "dem_factor_f"
    dem_obs_67 = "dem_obs_67"
    dem_obs_72 = "dem_obs_72"
    dem_obs_77 = "dem_obs_77"
    dem_obs_82 = "dem_obs_82"
    dem_obs_88 = "dem_obs_88"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class Kind(StrEnum):
    LUMP = "LUMP"
    ANNUITY = "ANNUITY"
    DEMENTIA = "DEMENTIA"
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    VOID = "VOID"
    MATURITY = "MATURITY"
