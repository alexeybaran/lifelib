# Range declarations of the full conversion (K3), unchanged; the line numbers in
# the comments below refer to that conversion's text at 04d69db.
# Obseques_FR_S: declared parameter ranges (cells_param_size, model level) from the product limits; a
# (lower, stop) pair where the parameter is an absolute value. Sources (model folder, product-spec.md):
#   t < 1142: need_max 1140; pols_if(t+1)/pols_all(t+1) at t = proj_len-1 and pols_if(t+12) guarded t+12 <=
#     proj_len (:1197) -> max t = 1140 -> 1141 exclusive, +1 margin
{'cells_param_size': {'t': 1142}}
