# Term_KR_S: declared parameter sizes (cells_param_size, model level), only where Probe A showed a
# policy valid for the product raising on the traced range. Sources (model folder, product-spec.md):
#   x < 121: mort_table.csv column age, keys 19..120 (read by mort_rate_at_age :759 and acc_mort_rate_at_age :772
#     via data.mort_table().loc[(sex, x)]); mort_table_mean :785 iterates a in [x, x+m) on the same table; bound =
#     120+1. Admissible max attained age is only 90 (90세만기)
#   m < 72: mort_table_mean(x, m) :785 is called with m = term_len(k) (:1030/:1038) <= policy_term() <= 71 years
#     (90세만기 - 만19세, product-spec.md:169-170), or the anchor term_y=20 from prem_rate_table.csv; bound = 71+1
{'cells_param_size': {'x': 121, 'm': 72}}
