"""Shared model-side binding for typed policy projections."""

import json
from enum import IntEnum

import modelx

from . import typed_inputs


def read_contract(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _plain(value):
    if isinstance(value, IntEnum):
        return int(value)
    if isinstance(value, dict):
        return {_plain(key): _plain(item) for key, item in value.items()}
    return value


def _table(tables, name, value):
    layout = tables[name]
    if "group_key" in layout:
        child = layout["value"].split(":")[1]
        return {_plain(key): _table(tables, child, item) for key, item in value.items()}
    return dict(value, columns=tuple(layout["columns"]))


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


def prepare(model_path, directory, contract, overrides, payload):
    rows = {row["point_id"]: _plain(row) for row in payload["policies"]}
    if len(rows) != len(payload["policies"]):
        raise ValueError("duplicate point_id")
    keys = tuple(rows)
    model = modelx.read_model(model_path, name=model_path.name + "_Adjusted")
    try:
        if directory.resolve() != model_path.parent:
            model.Data.input_directory = directory.resolve()
            model.Data.input_dir.formula = input_dir
        projection = model.Projection
        for name, declaration in contract["references"].items():
            if declaration.get("source") == "policy":
                continue
            kind = declaration["type"]
            if kind.startswith("table:"):
                value = _table(contract["tables"], kind.split(":")[1],
                               payload["references"][name])
                setattr(projection, name, value)
            elif name in payload["references"]:
                setattr(projection, name, _plain(payload["references"][name]))
        for name in contract["enums"]:
            setattr(projection, name, getattr(overrides, name))
        for name in ("lookup", "previous", "contains", "first_key", "last_key",
                     "subtable", "has_group", "key_count", "key_at", "sum_f64"):
            setattr(projection, name, getattr(typed_inputs, name))
        projection.policy_rows = rows
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


def compiler_spec(contract):
    references = [name for name, item in contract["references"].items()
                  if item.get("source") != "policy"]
    return {"typed_spaces": {"Projection": {
        "contract": contract, "coordinate": "point_id", "domain": "policy_keys",
        "rows": "policy_rows", "references": references,
        "sum": {"name": "cashflows", "value": "net_cf", "length": "proj_len",
                "policy_total": "policy_cashflows"},
    }}}
