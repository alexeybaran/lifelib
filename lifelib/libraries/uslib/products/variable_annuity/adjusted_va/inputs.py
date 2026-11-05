from pathlib import Path

import pandas as pd

from .formulas import FeeResetRule, GmdbOption, RollupRule, StepupBasis


_CSV_TABLES = {
    "model_point_table": ("model_point_table.csv", "point_id"),
    "mort_table": ("mort_table.csv", ["age", "sex"]),
    "fund_table": ("fund_table.csv", ["fund_set", "sub_id"]),
    "return_scenario": ("return_scenario.csv", ["scenario_id", "sub_id", "t"]),
    "rate_scenario": ("rate_scenario.csv", ["scenario_id", "t"]),
    "gawa_pct_table": ("gawa_pct_table.csv", ["gawa_grid", "age_from"]),
    "cdsc_table": ("cdsc_table.csv", ["cdsc_schedule", "completed_years"]),
    "transaction_table": ("transaction_table.csv", ["txn_id", "t"]),
}

_POLICY_ENUMS = {
    "glwb_stepup_basis": StepupBasis,
    "gmdb_option": GmdbOption,
    "fee_reset_rule": FeeResetRule,
    "rollup_rule": RollupRule,
}

_POLICY = {name: kind for kind, names in (
    ("i64", "point_id age_at_entry wd_start_age duration_mth_init bonus_end_init"),
    ("str", "policy_id sex designated_lives tax_status fund_set glwb_option cdsc_schedule scenario_id txn_id"),
    ("f64", "pols_if_init premium_tax_rate premium wd_intensity av_init gwb_init gawa_init "
            "gawa_pct_init bb_init rb_init np_init rp_init adj_init"),
) for name in names.split()}
_POLICY.update({field: f"enum:{enum.__name__}" for field, enum in _POLICY_ENUMS.items()})

_LEAVES = {
    "FundRows": ("alloc", "fund_expense"),
    "ReturnRows": ("gross_return",),
    "RateRows": ("rate",),
    "TransactionRows": ("prem_amount", "wd_amount"),
    "GawaRows": ("gawa_pct",),
    "ChargeRows": ("surr_charge_rate",),
    "MortalityRows": ("mort_rate",),
}
_GROUPS = {
    "FundSets": ("str", "FundRows"),
    "FundsById": ("i64", "ReturnRows"),
    "FundScenarios": ("str", "FundsById"),
    "RateColumns": ("str", "RateRows"),
    "RateScenarios": ("str", "RateColumns"),
    "Transactions": ("str", "TransactionRows"),
    "GawaSchedules": ("str", "GawaRows"),
    "ChargeSchedules": ("str", "ChargeRows"),
    "MortalityGroups": ("str", "MortalityRows"),
}
_TABLES = {
    "fund_table": ("fund_table", "FundSets"),
    "fund_returns": ("return_scenario", "FundScenarios"),
    "rate_scenarios": ("rate_scenario", "RateScenarios"),
    "transaction_table": ("transaction_table", "Transactions"),
    "gawa_table": ("gawa_pct_table", "GawaSchedules"),
    "cdsc_table": ("cdsc_table", "ChargeSchedules"),
    "mortality_table": ("mort_table", "MortalityGroups"),
}

def read_tables(directory):
    directory = Path(directory)
    return {name: pd.read_csv(directory / filename, index_col=index)
            for name, (filename, index) in _CSV_TABLES.items()}


def _pack_rows(frame, table):
    if table in _GROUPS:
        _, child = _GROUPS[table]
        return {key: _pack_rows(group.droplevel(0), child)
                for key, group in frame.groupby(level=0, sort=False)}
    if table != "FundRows":
        frame = frame.sort_index()
    return {"keys": frame.index.tolist(),
            "values": frame[list(_LEAVES[table])].to_numpy(dtype=float).tolist()}


def _pack_rate_columns(frame):
    # A string selects a numeric series just like the original column selector.
    scenarios = {}
    for scenario, group in frame.groupby(level=0, sort=False):
        rows = group.droplevel(0)
        columns = {}
        for name in rows:
            try:
                rates = rows[name].astype(float)
            except (TypeError, ValueError):
                continue  # e.g. source provenance, which is not a numeric series
            columns[name] = _pack_rows(rates.to_frame("rate"), "RateRows")
        scenarios[scenario] = columns
    return scenarios


def load_inputs(directory):
    tables = read_tables(directory)
    points = tables["model_point_table"]
    if not points.index.is_unique:
        raise ValueError("model_point_table.csv: duplicate point_id")
    for field, enum in _POLICY_ENUMS.items():
        try:
            points[field] = [int(enum[label]) for label in points[field]]
        except KeyError as error:
            raise ValueError(f"model_point_table.csv: invalid {field} {error.args[0]!r}") from error
    mortality = tables["mort_table"]
    if mortality.empty:
        raise ValueError("mort_table.csv: expected at least one mortality row")
    references = {"mortality_max_age": int(mortality.index.get_level_values("age").max())}
    for reference, (name, table) in _TABLES.items():
        frame = tables[name]
        if table == "RateScenarios":
            references[reference] = _pack_rate_columns(frame)
        else:
            if table == "MortalityGroups":
                frame = frame.reorder_levels(["sex", "age"])
            references[reference] = _pack_rows(frame, table)
    return {"policies": points.reset_index()[list(_POLICY)].to_dict("records"), "references": references}
