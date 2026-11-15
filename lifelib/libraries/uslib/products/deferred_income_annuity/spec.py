# DIA_US_S: declared parameter sizes (cells_param_size, model level), only where Probe A showed a
# policy valid for the product raising on the traced range. Sources (model folder, product-spec.md):
#   t < 1206: need_max 1200 + 5 (lives_if(a + j) with j < accel_months = 6, accel_cost line 1403 /
#     annuity_pp_sched(a+j) line 1574; a = accel_mth < proj_len) + 1 margin = 1206. lives_if(t+1) (line 811) and
#     annuity_factor loop s <= horizon_mths (line 929) are within this.
{'cells_param_size': {'t': 1206}}
