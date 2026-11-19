"""The model-point columns the DV01 Spaces read (conversion rule R5: a column chosen by an argument is an enum).
Members carry no meaning in their values; each branch of Data.numeric_field / Data.label_field reads its literal
column."""
from enum import IntEnum


class PolicyField(IntEnum):
    premium = 0
    gmir = 1
    free_wd_rate = 2
    pols_if_init = 3
    mgsv_rate = 4
    mgsv_annual_charge = 5
    premium_tax_rate = 6
    age_at_entry = 7
    free_wd_mva_exempt = 8
    free_wd_rule = 9
    sex = 10
    wd_schedule_id = 11
    renewal_architecture = 12
    mgsv_wd_convention = 13
    mva_family = 14
    mva_cap_rule = 15


NUMERIC = (PolicyField.premium, PolicyField.gmir, PolicyField.free_wd_rate, PolicyField.pols_if_init,
           PolicyField.mgsv_rate, PolicyField.mgsv_annual_charge, PolicyField.premium_tax_rate,
           PolicyField.age_at_entry, PolicyField.free_wd_mva_exempt)
LABEL = (PolicyField.free_wd_rule, PolicyField.sex, PolicyField.wd_schedule_id, PolicyField.renewal_architecture,
         PolicyField.mgsv_wd_convention, PolicyField.mva_family, PolicyField.mva_cap_rule)


def field_cell(name, table, cast, members):
    """The formula text of a field Cell: one branch per member, each a literal column; else ValueError."""
    lines = [f'def {name}(policy_id, field):']
    for number, member in enumerate(members):
        lines.append(f"    {'if' if number == 0 else 'elif'} field == PolicyField.{member.name}:")
        lines.append(f"        return {cast}({table}.loc[policy_id, {member.name!r}])")
    lines += ['    else:', f'        raise ValueError("invalid {name} field")', '']
    return '\n'.join(lines)
