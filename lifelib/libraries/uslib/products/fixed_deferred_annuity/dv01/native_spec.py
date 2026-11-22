"""Native compilation ranges for the MYGA DV01 example."""


def native_spec(model):
    # Competitor quotes use the remaining guarantee period. Renewal and
    # fixing quotes use 12 or 60 months. MVA rounds the remaining term at
    # month end, so zero must also be representable.
    years = model.Data.model_point_table()["guar_period"].max()
    tenor_count = max(60, 12 * int(years)) + 1
    policy_months = 1202
    curve_months = 1801
    return {"spaces": {
        "ESG": {"cells_param_size": dict.fromkeys(("i", "j", "m", "k"), curve_months)},
        "Market": {
            "cells_param_size": {
                "maturity_month": curve_months, "tenor_month": curve_months,
                ("tenor_month", "forward_month"): (tenor_count, policy_months),
            },
            # Budget one 0..60 quote axis for the shipped five-year book.
            # A wider book can fall back to the existing sparse storage.
            "cells": {"rate": {"max_dense_entries": 61 * policy_months}},
        },
        "Actual": {"cells_param_size": {"t": policy_months, "y": 101}},
        "Valuation": {"cells_param_size": {"t": policy_months, "y": 101, "k": (-1, 481)}},
        "Outer": {"cells_param_size": {"month": int(model.ESG.step_size()) + 1,
                                       "valuation_month": int(model.ESG.step_size()) + 1,
                                       "scen_id": (1, int(model.ESG.scen_size()) + 1),
                                       "key": 2147483647}},
    }}
