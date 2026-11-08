"""Shared model-side binding for typed policy projections."""

from enum import IntEnum

import modelx

from . import typed_inputs
from .immutable_inputs import freeze


def policy_cashflows():
    total = 0.0
    for t in range(proj_len()):
        total += net_cf(t)
    return total


def collect_outputs():
    return {"sum": {"cashflows": policy_cashflows()}}


def direct_total():
    return sum(Projection[point_id].policy_cashflows() for point_id in policy_keys)


def input_dir():
    return input_directory


def prepare(model_path, directory, overrides, payload, *, extra_helpers=()):
    rows = {row["point_id"]: row for row in payload["policies"]}
    if len(rows) != len(payload["policies"]):
        raise ValueError("duplicate point_id")
    keys = tuple(rows)
    model = modelx.read_model(model_path, name=model_path.name + "_Adjusted")
    try:
        if directory.resolve() != model_path.parent:
            model.Data.input_directory = directory.resolve()
            model.Data.input_dir.formula = input_dir
        projection = model.Projection
        for name, value in payload["references"].items():
            setattr(projection, name, freeze(value) if type(value) is dict else value)
        enum_names = []
        for name, value in vars(overrides).items():
            if isinstance(value, type) and issubclass(value, IntEnum) and value is not IntEnum:
                setattr(projection, name, value)
                enum_names.append(name)
        projection.enum_definitions = typed_inputs.EnumDefinitions(enum_names)
        for name in ("lookup", "previous", "contains", "first_key", "last_key",
                     "subtable", "has_group", "key_count", "key_at", "sum_f64", "sum_helper", "all_true",
                     *extra_helpers):
            setattr(projection, name, getattr(typed_inputs, name))
        projection.policy_rows = freeze(rows)
        projection.policy_keys = keys
        model.policy_keys = keys
        for name in overrides.CELLS:
            formula = getattr(overrides, name)
            if name in projection.cells:
                cell = projection.cells[name]
                doc = cell.doc
                cell.formula = formula
                if doc:
                    cell.doc = doc
            else:
                projection.new_cells(name, formula=formula)
        projection.new_cells("policy_cashflows", formula=policy_cashflows)
        projection.new_cells("collect_outputs", formula=collect_outputs)
        projection._impl.set_collect_spec({"point_id": keys})
        portfolio = model.new_space("Portfolio", refs={"Projection": projection, "policy_keys": keys})
        portfolio.new_cells("direct_total", formula=direct_total)
        return model
    except BaseException:
        model.close()
        raise
