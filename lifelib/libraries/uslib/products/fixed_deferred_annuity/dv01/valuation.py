"""Connect prospective canonical MYGA calculations to observed Actual history."""

from . import actual


def contract_point(valuation_month, policy_id, shock=-1):
    return {'refs': {'point_id': policy_id}}


def actual_history(t, name):
    return Actual[policy_id].contract_history(t, name)


def competitor_tenor(t):
    term = 12 * guar_period()
    if renewal_architecture() == Renewal.annual_redeclare and t >= term:
        return 1.0
    return (term * gp_index(t) - t) / 12.0


def competitor_rate(t):
    if t < valuation_month:
        return Actual[policy_id].market_rate(t)
    return market().rate(t - valuation_month, competitor_tenor(t))


def renewal_quote(t):
    tenor = 1.0 if renewal_architecture() == Renewal.annual_redeclare else 5.0
    return market().rate(t - valuation_month, tenor)


def renewal_crediting_spread(t):
    return market().spread(t - valuation_month)


def mva_current_yield(t):
    if t < valuation_month:
        return Actual[policy_id].mva_ref_yield(t)
    return market().rate(t - valuation_month, mva_term(t))


def mva_fixing_yield(t):
    return market().rate(t - valuation_month, 5.0)


def credit_rate(t):
    if t < 12 * guar_period():
        return declared_rate_initial()
    start = redeclare_month(t)
    if start <= valuation_month:
        return actual_history(t if t < valuation_month else valuation_month, 'booked_credit')
    return max(gmir(), renewal_quote(start) - renewal_crediting_spread(start))


def mva_ref_yield_locked(t):
    if gp_index(t) <= 1:
        return mva_ref_yield_at_issue()
    start = gp_start_month(t)
    if start <= valuation_month:
        return actual_history(t if t < valuation_month else valuation_month, 'booked_mva')
    return mva_fixing_yield(start)


def net_cf(t):
    month = valuation_month + t
    contract = contract_projection()
    return contract.net_cf(month) if 0 <= t < HORIZON and month < contract.proj_len() else 0.0


def policy_state(t):
    return contract_projection().policy_state(valuation_month + t)


def mgsv_open(t):
    month = valuation_month + t
    contract = contract_projection()
    return contract.mgsv_pp(month - 1) if month else contract.mgsv_pp_init()


def interest_cum_open(t):
    month = valuation_month + t
    return contract_projection().interest_credited_pp(month - 1) if month else 0.0


def interest_ytd_open(t):
    month = valuation_month + t
    year_start = month // 12 * 12
    return interest_cum_open(t) - (contract_projection().interest_credited_pp(year_start - 1) if year_start else 0.0)


def interest_ytd_eom(t):
    month = valuation_month + t
    year_start = month // 12 * 12
    contract = contract_projection()
    return contract.interest_credited_pp(month) - (contract.interest_credited_pp(year_start - 1) if year_start else 0.0)


def prem_gmir_open(t):
    month = valuation_month + t
    contract = contract_projection()
    return contract.prem_accum_gmir_pp(month - 1) if month else contract.premium_pp()


def mva_amount(t, is_wd):
    month = valuation_month + t
    contract = contract_projection()
    base = contract.wd_excess_pp(month) if is_wd == 1 else contract.surr_excess_pp(month)
    return contract.mva_pp_on(month, base)


def claims(t):
    month = valuation_month + t
    contract = contract_projection()
    return contract.claims(month, Kind.ALL) if 0 <= month < contract.proj_len() else 0.0


def anniversary(t):
    month = valuation_month + t
    return float(0 < month < contract_projection().proj_len() and month % 12 == 0)


def redeclare(t):
    month = valuation_month + t
    contract = contract_projection()
    return float(0 < month < contract.proj_len() and month == contract.redeclare_month(month))


def install_local_accessors(valuation, refs):
    valuation.new_cells('contract_projection', 'lambda: ValuationContract')
    valuation.new_cells('in_contract', 'lambda t: valuation_month + t < contract_projection().proj_len()')
    for kind in ('AvTiming', 'PolTiming', 'Kind'):
        setattr(valuation, kind, refs[kind])
    no_args = ('premium_pp', 'gmir', 'mgsv_rate', 'pols_if_init', 'age_at_entry', 'sex', 'renewal_architecture')
    for name in no_args:
        valuation.cells[name].formula = f'lambda: contract_projection().{name}()'
    fields = {'mgsv_charge': 'mgsv_annual_charge', 'free_rate': 'free_wd_rate', 'premium_tax': 'premium_tax_rate',
              'free_exempt': 'free_wd_mva_exempt'}
    for name, target in fields.items():
        valuation.cells[name].formula = f'lambda: float(contract_projection().{target}())'
    same_names = ('credit_rate', 'credit_rate_mth', 'free_wd_avail', 'wd_pp', 'wd_free_pp', 'free_wd_remain',
                  'wd_excess_pp', 'mva_in_force', 'surr_excess_pp', 'surr_charge_pp', 'wd_charge_pp', 'mva_rate',
                  'mva_pp', 'wd_mva_pp', 'wd_payment_pp', 'surr_value_pp', 'surr_benefit_pp', 'lapse_dyn_market',
                  'lapse_dyn_rate', 'lapse_rate', 'lapse_rate_mth', 'pols_death', 'pols_lapse', 'pols_maturity',
                  'age', 'gp_index', 'mva_term', 'market_rate', 'mva_ref_yield')
    shifted = {**{name: name for name in same_names},
               'mva_ref_locked': 'mva_ref_yield_locked', 'av_eom': 'av_pp', 'interest_month': 'inv_income_pp',
               'interest_cum_eom': 'interest_credited_pp', 'prem_gmir_eom': 'prem_accum_gmir_pp',
               'mgsv_wd_deduct': 'mgsv_wd_deduct_pp', 'mgsv_eom': 'mgsv_pp', 'ann_rate': 'annuitization_rate',
               'pols_open': 'pols_if', 'pols_ann': 'pols_annuitization', 'market_tenor': 'competitor_tenor',
               'mort': 'mort_rate_mth', 'wd': 'wd_scheduled_pp', 'surr_charge': 'surr_charge_rate',
               'lapse_base': 'lapse_rate_base', 'lapse_power': 'lapse_dyn_exponent', 'inflation': 'inflation_factor',
               'premium': 'premiums', 'withdrawal_cf': 'withdrawals', 'commission_cf': 'commissions',
               'premium_tax_cf': 'premium_taxes', 'expense_cf': 'expenses', 'declaration_yield': 'renewal_quote',
               'mva_lock_yield': 'mva_fixing_yield'}
    expires = {'mva_term', 'market_rate', 'mva_ref_yield', 'declaration_yield', 'mva_lock_yield', 'mort',
               'wd', 'wd_pp', 'wd_free_pp', 'wd_excess_pp', 'wd_charge_pp', 'wd_mva_pp', 'wd_payment_pp',
               'mva_rate', 'surr_charge', 'surr_charge_pp', 'lapse_base', 'lapse_power', 'inflation',
               'pols_ann', 'pols_death', 'pols_lapse', 'pols_maturity', 'withdrawal_cf'}
    for name, target in shifted.items():
        expression = f'lambda t: contract_projection().{target}(valuation_month + t)'
        if name in expires:
            expression += ' if in_contract(t) else 0.0'
        if name == 'mva_in_force':
            expression += ' if in_contract(t) else False'
        valuation.cells[name].formula = expression
    adapters = {'net_cf': net_cf, 'policy_state': policy_state, 'mgsv_open': mgsv_open, 'claims': claims,
                'interest_cum_open': interest_cum_open, 'interest_ytd_open': interest_ytd_open,
                'interest_ytd_eom': interest_ytd_eom, 'prem_gmir_open': prem_gmir_open, 'mva_amount': mva_amount,
                'anniversary': anniversary, 'redeclare': redeclare,
                'av_open': 'lambda t: contract_projection().av_pp_at(valuation_month + t, AvTiming.BEF_WD)',
                'av_bef_inv': 'lambda t: contract_projection().av_pp_at(valuation_month + t, AvTiming.BEF_INV)',
                'pols_after_ann': 'lambda t: contract_projection().pols_if_at(valuation_month + t, PolTiming.BEF_MORT)'
                                  ' if in_contract(t) else 0.0',
                'pols_after_mort': 'lambda t: contract_projection().pols_if_at(valuation_month + t, PolTiming.BEF_LAPSE)'
                                   ' if in_contract(t) else 0.0',
                'pols_after_lapse': 'lambda t: contract_projection().pols_if_at(valuation_month + t, PolTiming.AFT_DECR)'
                                    ' if in_contract(t) else 0.0',
                'pols_eom': 'lambda t: contract_projection().pols_if(valuation_month + t + 1)',
                'gp_window': 'lambda t: float(in_contract(t) and contract_projection().in_gp_window(valuation_month + t))',
                'maturity': 'lambda t: float(valuation_month + t == contract_projection().proj_len() - 1)'}
    for name, formula in adapters.items():
        valuation.cells[name].formula = formula


def install(valuation, observed, data, market, sources, refs):
    valuation.data = data
    owner_cells = ('model_point', 'has_withdrawals', 'withdrawal_rows')
    for name in owner_cells:
        valuation.cells[name].formula = sources[name]
    contract = valuation.new_space('ValuationContract', refs={
        **refs, 'Actual': observed, 'data': data, 'Scenarios': market})
    contract.relref(**{name: valuation.cells[name] for name in owner_cells})
    contract.relref(valuation_market=valuation.cells['market'])
    boundary = {'av_pp': 'av', 'mgsv_pp': 'mgsv', 'interest_credited_pp': 'interest',
                'prem_accum_gmir_pp': 'gmir_premium', 'pols_if': 'in_force',
                'free_wd_remain': 'remaining_allowance', 'tax_basis_pp': 'tax_basis'}
    for name, source in sources.items():
        if name in owner_cells:
            continue
        if name in boundary:
            kernel = 'contract_' + name
            contract.new_cells(kernel, source)
            comparison = '<=' if name == 'pols_if' else '<'
            contract.new_cells(name, f"lambda t: actual_history(t, {boundary[name]!r}) "
                               f"if t {comparison} valuation_month else {kernel}(t)")
        else:
            contract.new_cells(name, source)
    adapters = {'market': 'lambda: valuation_market()',
                'market_rate': competitor_rate, 'competitor_tenor': competitor_tenor, 'renewal_quote': renewal_quote,
                'renewal_crediting_spread': renewal_crediting_spread,
                'mva_ref_yield': mva_current_yield, 'mva_fixing_yield': mva_fixing_yield,
                'credit_rate': credit_rate, 'mva_ref_yield_locked': mva_ref_yield_locked,
                'actual_history': actual_history, 'policy_state': actual.policy_state}
    for name, formula in adapters.items():
        if name in contract.cells:
            contract.cells[name].formula = formula
        else:
            contract.new_cells(name, formula)
    install_local_accessors(valuation, refs)
