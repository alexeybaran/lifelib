#!/bin/bash
# ir_d0.sh ENVFILE BUILD TAG : D0 method, cachegrind without cache simulation, Ir(setup+report) - Ir(setup), book 1,050
source /home/user/c5/$1; B=$2; T=$3; O=/home/user/c5/res/ir; mkdir -p $O
for p in setup report; do
  x=; [ $p = setup ] && x=--setup-only
  valgrind --tool=cachegrind --cache-sim=no --cachegrind-out-file=/dev/null $PY -B /home/user/c5/scripts/pool_run_c5.py $B /home/user/c5/books/book-1050 1 $O/$T-$p.json --steps 2 --paths 1 $x > $O/$T-$p.log 2>&1 &
done
wait
s=$(grep -h 'I *refs' $O/$T-setup.log | awk '{gsub(",","",$NF); print $NF}'); r=$(grep -h 'I *refs' $O/$T-report.log | awk '{gsub(",","",$NF); print $NF}')
echo "{\"tag\": \"$T\", \"ir_setup\": $s, \"ir_report_process\": $r, \"ir_report\": $((r - s)), \"ir_per_policy\": $(( (r - s) / 1050 ))}" | tee $O/$T.json
