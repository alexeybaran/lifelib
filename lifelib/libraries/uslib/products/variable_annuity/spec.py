# VA_US_S: declared parameter sizes (cells_param_size, model level), only where Probe A showed a
# policy valid for the product raising on the traced range. Sources (model folder, product-spec.md):
#   t < 963: need_max 960 + 2 (scenario_rate(t_of_month(3*k-1)) with k = contract_quarter(t) reaches month
#     duration_mth(t)+2, vix_sq line 806 / phi_glwb_vix line 1292) + 1 margin = 963. pols_if(t+1) (av_at line 2303,
#     check_pols_roll_fwd_resid line 2376) is within.
{'cells_param_size': {'t': 963}}
