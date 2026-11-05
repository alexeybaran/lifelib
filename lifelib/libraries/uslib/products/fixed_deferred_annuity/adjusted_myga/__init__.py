"""Prepare the original US MYGA model for typed projection."""

from pathlib import Path

from lifelib import _typed_projection

from . import formulas
from .inputs import load_inputs


_HERE = Path(__file__).resolve().parent


def prepare(directory=_HERE.parent):
    """Return a live adjusted model. Close it after use."""
    contract = _typed_projection.read_contract(_HERE / "contract.json")
    return _typed_projection.prepare(_HERE.parent / "MYGA_US_S", Path(directory), contract,
                                     formulas, load_inputs(directory))


def compiler_spec():
    return _typed_projection.compiler_spec(_typed_projection.read_contract(_HERE / "contract.json"))
