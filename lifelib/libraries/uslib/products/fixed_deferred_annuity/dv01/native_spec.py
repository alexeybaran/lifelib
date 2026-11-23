"""Native compilation ranges for the MYGA DV01 example."""


def native_spec(model):
    # Competitor quotes use the remaining guarantee period. Renewal and
    # fixing quotes use 12 or 60 months. MVA rounds the remaining term at
    # month end, so zero must also be representable.
    years = model.Data.model_point_table()["guar_period"].max()
    tenor_count = max(60, 12 * int(years)) + 1
    book_end = model.Data.book_projection_end()
    policy_months = max(1202, book_end + 2)
    curve_months = 1801
    close_months = int(model.ESG.step_size()) + 1
    return {"spaces": {
        "ESG": {"cells_param_size": {**dict.fromkeys(("i", "j", "m", "k"), curve_months),
                                     "scen_id": (1, int(model.ESG.scen_size()) + 1)}},
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
        "Valuation": {"cells_param_size": {"t": policy_months, "y": 101, "k": (-1, policy_months),
                                           "month": (-1, close_months)}},
        "Outer": {"cells_param_size": {"month": (-1, close_months), "valuation_month": (-1, close_months),
                                       "scen_id": (1, int(model.ESG.scen_size()) + 1),
                                       "num_scenarios": (1, int(model.ESG.scen_size()) + 1),
                                       "annual_steps": (close_months - 2) // 12 + 1,
                                       "key": 2147483647}},
    }}
