"""Category names at the saved models' input boundaries."""

from contextlib import contextmanager

import modelx as mx
from modelx.core.errors import FormulaError
from modelx_helpers import pdn
import pytest

from us_registry import model_path


@contextmanager
def saved_model(name):
    model = mx.read_model(model_path(name))
    try:
        yield model
    finally:
        model.close()


def set_policy_fields(projection, **changes):
    fields = dict(projection.model_point())
    fields.update(changes)
    projection.model_point[()] = pdn.Record(fields, preserve_scalar_types=True)


@pytest.mark.parametrize(
    "model_name, field, enum_name, sentinel",
    [
        ("RILA_US_S", "crediting_type", "CreditType", "INVALID"),
        ("RILA_US_S", "iv_family", "InterimValueFamily", "INVALID"),
        ("RILA_US_S", "amort_rule", "Amortization", "INVALID"),
        ("ULSG_US_S", "premium_type", "PremiumType", "UNKNOWN"),
        ("ULSG_US_S", "premium_mode", "PremiumMode", "UNKNOWN"),
        ("UL_US_S", "db_option", "DeathBenefitOption", "OTHER"),
        ("UL_US_S", "qual_test", "Qualification", "OTHER"),
        ("UL_US_S", "premium_type", "PremiumType", "OTHER"),
        ("WholeLife_US_S", "dividend_option", "DividendOption", "OTHER"),
    ],
)
def test_policy_category_requires_a_label(model_name, field, enum_name, sentinel):
    with saved_model(model_name) as model:
        projection = model.Projection[1]
        conversion = projection.cells[field]
        enum = getattr(projection, enum_name)
        expected = enum[projection.model_point()[field]]
        assert conversion() is expected

        for value in ("unrecognized_label", sentinel, expected):
            set_policy_fields(projection, **{field: value})
            assert projection.model_point()[field] is value
            with pytest.raises(FormulaError):
                conversion()
            error = mx.get_error()
            assert isinstance(error, KeyError)
            assert error.args == (value,)


def test_nonparticipating_whole_life_dividend_label():
    with saved_model("WholeLife_US_S") as model:
        for point in (11, 12, 13):
            projection = model.Projection[point]
            assert projection.model_point()["dividend_option"] == "NONE"
            assert projection.dividend_option() is projection.DividendOption.NONE
            assert int(projection.dividend_option()) == -1
            assert projection.div_credited(11) == 0.0


def test_dia_life_only_with_return_of_premium():
    with saved_model("DIA_US_S") as model:
        projection = model.Projection[1]
        set_policy_fields(projection, income_form="LO_ROP", db_form="ROP")
        assert projection.income_form() == "LO_ROP"
        assert projection.payout_form() is projection.PayoutForm.LO
        assert projection.db_form() is projection.DeathBenefit.ROP

        for value in ("unrecognized_label", "INVALID", projection.PayoutForm.LO):
            set_policy_fields(projection, income_form=value)
            with pytest.raises(FormulaError, match="invalid income_form"):
                projection.payout_form()


def test_spia_discount_convention_raises_at_conversion():
    with saved_model("SPIA_US_S") as model:
        projection = model.Projection
        enum = projection.DiscountConvention
        for label, expected in (("compound", enum.COMPOUND), ("simple", enum.SIMPLE)):
            projection.commute_disc_convention = label
            assert projection.commute_discount_code() is expected

        for value in ("unrecognized_label", "COMPOUND", "INVALID", enum.COMPOUND):
            projection.commute_disc_convention = value
            with pytest.raises(FormulaError, match="invalid commute_disc_convention"):
                projection.commute_discount_code()


def test_myga_schedule_input_rejects_unknown_group(tmp_path):
    with saved_model("MYGA_US_S") as model:
        data = model.Data
        enum = data.Schedule
        groups = tuple(data.surr_charge_table())
        assert groups == (enum.initial, enum.renewal)
        assert all(isinstance(group, enum) for group in groups)

        path = tmp_path / "schedules.csv"
        path.write_text(
            "schedule,contract_year,surr_charge_rate\nunknown_schedule,1,0.09\n",
            encoding="utf-8",
        )
        data.surr_charge_file = path
        with pytest.raises(FormulaError):
            data.surr_charge_table()
        error = mx.get_error()
        assert isinstance(error, KeyError)
        assert error.args == ("unknown_schedule",)
