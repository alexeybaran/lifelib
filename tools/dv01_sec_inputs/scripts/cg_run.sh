#!/bin/bash
# cg_run.sh ENVFILE BUILD BOOK TAG DRIVER WORKERS [extra]: callgrind (cache sim) of setup-only and setup+report
source /home/user/c5/$1; B=$2; BOOK=$3; T=$4; D=$5; W=$6; shift 6; O=${CGO:-/home/user/c5/res/cg2}; mkdir -p $O
for p in setup report; do
  x=; [ $p = setup ] && x=--setup-only
  valgrind --tool=callgrind --cache-sim=yes --D1=49152,12,64 --LL=16777216,16,64 --callgrind-out-file=$O/$T-$p.out $PY -B /home/user/c5/scripts/$D $B $BOOK $W $O/$T-$p.json --steps 2 --paths 1 $x "$@" > $O/$T-$p.log 2>&1 &
done
wait
