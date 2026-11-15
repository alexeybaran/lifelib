# TD_FR_S: declared parameter sizes (cells_param_size, model level), only where Probe A showed a
# policy valid for the product raising on the traced range. Sources (model folder, product-spec.md):
#   t < 686: need_max 684; pols_if(t+1) in check_pols_roll_fwd_resid/check_decrement_closure_resid -> max t = 684 ->
#     685 exclusive, +1 margin
{'cells_param_size': {'t': 686}}
