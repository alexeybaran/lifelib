"""Prepare the original US MYGA model for typed projection."""

from pathlib import Path

from lifelib import _typed_projection

from . import formulas
from .inputs import load_inputs


_HERE = Path(__file__).resolve().parent


def prepare(directory=_HERE.parent):
    """Return a live adjusted model. Close it after use."""
    return _typed_projection.prepare(_HERE.parent / "MYGA_US_S", Path(directory),
                                     formulas, load_inputs(directory))
