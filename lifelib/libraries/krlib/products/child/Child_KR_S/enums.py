"""Label families passed as cell arguments in Child_KR_S, stored with the model.

Each member's value is upstream's label text: a member equals, hashes and prints
as its label (``Kind.DEATH == "DEATH"``).  Python 3.11 or later."""

from enum import StrEnum


class Sex(StrEnum):
    M = "M"
    F = "F"


class LapseColumn(StrEnum):
    first_year_rate = "first_year_rate"
    completion_rate = "completion_rate"
    ultimate_rate = "ultimate_rate"


class Cover(StrEnum):
    disability = "disability"
    disease_disab = "disease_disab"
    cancer = "cancer"
    minor_cancer = "minor_cancer"
    cerebral = "cerebral"
    cardiac = "cardiac"
    surgery = "surgery"
    fracture = "fracture"
    burn = "burn"
    hosp_acc = "hosp_acc"
    hosp_dis = "hosp_dis"
    liability = "liability"
    neonatal = "neonatal"


class Kind(StrEnum):
    DISABILITY = "DISABILITY"
    DIAGNOSIS = "DIAGNOSIS"
    SURGERY = "SURGERY"
    HOSPITAL = "HOSPITAL"
    EVENT = "EVENT"
    LIABILITY = "LIABILITY"
    NEONATAL = "NEONATAL"
    DEATH = "DEATH"
    LAPSE = "LAPSE"
    MATURITY = "MATURITY"
    VOID = "VOID"


class PolTiming(StrEnum):
    BEF_DECR = "BEF_DECR"
    BEF_LAPSE = "BEF_LAPSE"
    AFT_DECR = "AFT_DECR"


class NeoTiming(StrEnum):
    birth = "birth"
    block = "block"


class BasisParam(StrEnum):
    disab_severity = "disab_severity"
    disease_disab_severity = "disease_disab_severity"
    surgery_rate_cancer = "surgery_rate_cancer"
    surgery_rate_cerebral = "surgery_rate_cerebral"
    surgery_rate_cardiac = "surgery_rate_cardiac"
    liability_severity = "liability_severity"
    hosp_cap_factor = "hosp_cap_factor"
    waiver_disab_share = "waiver_disab_share"
    payer_disab_ratio = "payer_disab_ratio"
    leak_share = "leak_share"
    void_rate_ann = "void_rate_ann"
    broad_def_factor = "broad_def_factor"
    net_prem_ratio = "net_prem_ratio"
