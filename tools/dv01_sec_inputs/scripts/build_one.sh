#!/bin/bash
# build_one.sh ENVFILE NAME PKG OPTIONS ROUTE : export with scripts/export_d.py then compile
set -e
source /home/user/c5/$1; NAME=$2
B=$DV01SEC_ROOT/build/$NAME; rm -rf $B
t0=$(date +%s)
DV01_PKG=$3 DV01_OPTIONS=$4 $PY -B /home/user/c5/scripts/export_d.py $B $5 > /home/user/c5/work/export-$NAME.log 2>&1
t1=$(date +%s)
cd /home/user/c5/scripts && $PY compile_dir.py $NAME > /home/user/c5/work/compile-$NAME.log 2>&1
t2=$(date +%s)
echo "{\"build\": \"$NAME\", \"export_s\": $((t1-t0)), \"compile_s\": $((t2-t1))}" | tee -a /home/user/c5/work/compile-seconds.jsonl
