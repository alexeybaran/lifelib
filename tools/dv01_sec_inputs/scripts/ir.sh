#!/bin/bash
# ir.sh TAG NAME COMPILER MODELX : instructions per point inside item build, result_cf and release (S2 method)
T=$1; N=$2; export PYTHONPATH=$3:$4:/home/user/c5/lifelib PYTHONHASHSEED=0
for rep in 1 2 3; do for p in 1 4; do
  valgrind --tool=callgrind --callgrind-out-file=/dev/null --toggle-collect='*_mx_new_root__c_Projection*' \
    --toggle-collect='*_c_Projection*result_cf*' --toggle-collect='*_mx_release_item__c_Projection*' \
    /home/user/c5/env/bin/python -B /home/user/c5/sec/ir_sec.py /home/user/c5/sec/$T-$N $N $p 2>&1 | grep -E "Collected|^points" | tr '\n' ' ' | sed "s/^/$T $N $rep $p /"; echo
done; done
