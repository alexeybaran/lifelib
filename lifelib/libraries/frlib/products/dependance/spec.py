# Dep_FR_S: declared parameter sizes (cells_param_size, model level), only where Probe A showed a
# policy valid for the product raising on the traced range. Sources (model folder, product-spec.md):
#   t < 842: need_max 840; check_states sweeps range(proj_len()+1) (:1927) and
#     pols_if/pols_part/pols_tot/pols_totr(t+1) in roll-fwd checks -> max t = 840 -> 841 exclusive, +1 margin
#   y < 73: policy year y = duration(t)+1 (:667); premium_factor(policy_year(t)), t<=840 -> y<=71 -> 72 exclusive,
#     +1 margin (revision_table.csv clamps at policy_year 6)
#   z < 843: claim duration cohorts 1..max_dur(); max_dur (:682) = proj_len()+claim_duration_months()+1; z0 <=
#     12*(attained age - 40) so z <= 12*(110-40)+1 = 841 -> 842 exclusive, +1 margin
#   n < 72: reduction_coeff(n) (:842), n = years_paid() or years_premiums_paid(t-1)=(t)//12 <= 70 = 110-40 -> 71
#     exclusive, +1 margin; reduction_table.csv years_paid 5..30 clamps at 30
{'cells_param_size': {'t': 842, 'y': 73, 'z': 843, 'n': 72}}
