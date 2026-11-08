from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from . import formulas


def load_declarations():
    return json.loads(Path(__file__).with_name("inputs.json").read_text(encoding="utf-8"))


def _text(text: str) -> str:
    return text


def _integer(text: str) -> int:
    value = int(text)
    if not -(1 << 63) <= value < (1 << 63):
        raise ValueError("integer outside signed 64-bit range")
    return value


def _number(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite input number")
    return value


def _boolean(text: str) -> bool:
    if text in ("True", "true", "1"):
        return True
    if text in ("False", "false", "0"):
        return False
    raise ValueError("expected a boolean")


def _converter(type_name: str):
    """Resolve the declared converter once, without inspecting any input value."""
    if type_name == "str":
        return _text
    if type_name == "i64":
        return _integer
    if type_name == "f64":
        return _number
    if type_name == "bool":
        return _boolean
    if type_name.startswith("enum:"):
        return getattr(formulas, type_name.removeprefix("enum:")).__getitem__
    raise ValueError(f"Unsupported input schema type {type_name!r}")


def _value(text: str, type_name: str, location: str) -> Any:
    """Parse a schema type; no categorical domains are learned from input data."""
    convert = _converter(type_name)
    try:
        return convert(text)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"{location}: invalid {type_name} value {text!r}") from exc


def _rows(path: Path, required: tuple[str, ...] | list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError(f"{path.name}: duplicate column names")
        missing = set(required).difference(fields)
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        result = []
        for line, row in enumerate(reader, 2):
            # A C-level value scan avoids the Python field-by-field check on
            # complete rows. Missing optional trailing columns remain allowed.
            if None in row or (None in row.values() and any(row[name] is None for name in required)):
                raise ValueError(f"{path.name}:{line}: malformed CSV row")
            result.append(row)
        return result


def _leaf(rows: list[dict[str, str]], key: str, columns: tuple[str, ...], filename: str) -> dict[str, list]:
    parsed = {}
    for line, row in enumerate(rows, 2):
        index = _value(row[key], "i64", f"{filename}:{line}:{key}")
        if index in parsed:
            raise ValueError(f"{filename}: duplicate table key {index}")
        parsed[index] = [_value(row[name], "f64", f"{filename}:{line}:{name}") for name in columns]
    keys = sorted(parsed)
    return {"keys": keys, "values": [parsed[index] for index in keys], "columns": columns}


def _table(directory: Path, filename: str, key: str, columns: tuple[str, ...], *,
           group: str | None = None, group_type: str = "str") -> dict:
    required = [key, *columns] + ([group] if group else [])
    rows = _rows(directory / filename, required)
    if group is None:
        return _leaf(rows, key, columns, filename)
    groups: dict[Any, list[dict[str, str]]] = {}
    for line, row in enumerate(rows, 2):
        name = _value(row[group], group_type, f"{filename}:{line}:{group}")
        groups.setdefault(name, []).append(row)
    return {name: _leaf(values, key, columns, filename) for name, values in groups.items()}


def load_inputs(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    schema = load_declarations()
    fields = schema["model_points"]
    converters = [(name, typ, _converter(typ)) for name, typ in fields.items()]
    policies = []
    point_ids = set()
    for line, row in enumerate(_rows(directory / "model_point_table.csv", list(fields)), 2):
        policy = {}
        try:
            for name, typ, convert in converters:
                policy[name] = convert(row[name])
        except (ValueError, KeyError) as exc:
            # Detailed locations are useful on failure, but need not be built
            # for each valid field in every input record.
            raise ValueError(f"model_point_table.csv:{line}:{name}: invalid {typ} value {row[name]!r}") from exc
        if policy["point_id"] in point_ids:
            raise ValueError(f"Duplicate point_id {policy['point_id']}")
        if policy["guar_period"] <= 0:
            raise ValueError(f"Policy {policy['point_id']}: guar_period must be positive")
        point_ids.add(policy["point_id"])
        policies.append(policy)

    references = {name: spec["default"] for name, spec in schema["assumptions"].items()}
    assumptions = directory / "assumptions.csv"
    if assumptions.exists():
        seen = set()
        for line, row in enumerate(_rows(assumptions, ["name", "value"]), 2):
            name = row["name"]
            if name not in references:
                raise ValueError(f"assumptions.csv:{line}: unknown scalar assumption {name!r}")
            if name in seen:
                raise ValueError(f"assumptions.csv:{line}: duplicate assumption {name!r}")
            seen.add(name)
            references[name] = _value(row["value"], schema["assumptions"][name]["type"], f"assumptions.csv:{line}:{name}")

    references.update({
        "mort_table": _table(directory, "mort_table.csv", "age", ("mort_rate",),
                             group="sex", group_type="enum:Sex"),
        "surr_charge_table": _table(directory, "surr_charge_table.csv", "contract_year", ("surr_charge_rate",),
                                    group="schedule", group_type="enum:Schedule"),
        "withdrawal_table": _table(directory, "withdrawal_table.csv", "t", ("wd_amount",),
                                    group="wd_schedule_id"),
        "rate_scenario": _table(directory, "rate_scenario.csv", "t", ("mva_ref_yield", "market_rate"),
                                 group="scenario_id"),
        "surr_charge_age_cap_table": _table(directory, "surr_charge_age_cap.csv", "age", ("surr_charge_cap",)),
        "mva_factor_table": _table(directory, "mva_factor_table.csv", "years_remaining", ("factor_lo", "factor_hi")),
    })
    return {"policies": policies, "references": references}
