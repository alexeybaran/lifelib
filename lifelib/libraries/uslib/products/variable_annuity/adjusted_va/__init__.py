"""Prepare the original US VA model for typed projection."""

from pathlib import Path

from lifelib import _typed_projection

from . import formulas
from .inputs import load_inputs


_HERE = Path(__file__).resolve().parent


def prepare(directory=_HERE.parent):
    """Return a live adjusted model. Close it after use."""
    return _typed_projection.prepare(_HERE.parent / "VA_US_S", Path(directory),
                                     formulas, load_inputs(directory), extra_helpers=("any_true", "max_value"))
