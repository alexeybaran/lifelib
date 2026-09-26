# modelx: pseudo-python
# This file is part of a modelx model.
# It can be imported as a Python module, but functions defined herein
# are model formulas and may not be executable as standard Python.

from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def model_point_table():
    return model_point_table_data


def mort_table():
    return mort_table_data


def surr_charge_table():
    return surr_charge_table_data


def surr_charge_age_cap_table():
    return surr_charge_age_cap_table_data


def rate_scenario():
    return rate_scenario_data


def withdrawal_table():
    return withdrawal_table_data


def mva_factor_table():
    return mva_factor_table_data


# ---------------------------------------------------------------------------
# References

model_point_table_data = ("Pickle", 1)

mort_table_data = ("Pickle", 2)

surr_charge_table_data = ("Pickle", 3)

surr_charge_age_cap_table_data = ("Pickle", 4)

rate_scenario_data = ("Pickle", 5)

withdrawal_table_data = ("Pickle", 6)

mva_factor_table_data = ("Pickle", 7)