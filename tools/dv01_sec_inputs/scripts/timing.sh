#!/bin/bash
# timing.sh OUTDIR ROUNDS "W..." ARM... ; ARM = env:buildpath:driver:tag
O=$1; R=$2; WS=$3; shift 3; mkdir -p $O/frames
echo "c5 timing $(date)" > /home/user/c5/TIMING.lock
for r in $(seq $R); do for w in $WS; do
  arms="$*"; [ $((r % 2)) = 0 ] && arms=$(echo $* | tr ' ' '\n' | tac | tr '\n' ' ')
  for a in $arms; do IFS=: read e b d t <<< "$a"; source /home/user/c5/$e
    pin="taskset -c 0"; [ $w = 4 ] && pin="taskset -c 0-3"; [ $w = 2 ] && pin="taskset -c 0-1"
    while [ $(awk '{print ($1 > 0.7)}' /proc/loadavg) = 1 ]; do sleep 3; done
    $pin $PY -B /home/user/c5/scripts/$d /home/user/c5/$b /home/user/c5/books/book-1050 $w $O/t-$t-$w-$r.json --steps 2 --paths 1 --frames $O/frames $EXTRA > /dev/null 2>>$O/stderr.log
    python3 -c "import json;d=json.load(open('$O/t-$t-$w-$r.json'));print('$r $w $t', round(d['wall'],2), round(d['cpu'],2), round(d['system'],2), round(d['peak_rss_mib']), d['minflt'], d['invol_cs'], d['dv01_total'])"
  done
done; done
rm -f /home/user/c5/TIMING.lock
