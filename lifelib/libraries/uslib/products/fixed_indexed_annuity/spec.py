# FIA_US_S: declared parameter sizes (cells_param_size, model level), only where Probe A showed a
# policy valid for the product raising on the traced range. Sources (model folder, product-spec.md):
#   t < 974: need_max 972 + 1 (pols_if(t+1) in av_at EOY line 2584 and check_pols_roll_fwd_resid line 2668) + 1
#     margin = 974
#   a < 121: attained age: payout_rate(exercise_age(t), ...) (line 1287), activation_rate(a) (line 1294, reported
#     only); max attained age = maturity_age 120 (also payout_rate_table.csv age_hi max 120); +1 = 121
{'cells_param_size': {'t': 974, 'a': 121}}
