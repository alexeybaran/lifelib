#!/bin/bash
# Run a model's own tests and the library tests parametrized by it, in a tree.
#   tools/lean/runtests.sh <tree> <lib> <product> <Model>
# Prints the pytest summary line.  --dist loadfile keeps each module's tests in order in
# one worker, so module-scoped fixtures see the same order as a sequential run.
tree=$1; lib=$2; product=$3; model=$4
cd "$tree/lifelib/libraries/$lib/tests" || exit 2
own=$(ls test_${product}_*.py 2>/dev/null | grep -v _sec.py)
shared=$(ls test_model_conventions*.py test_mortality_caps.py test_compiled_conventions.py 2>/dev/null)
python -m pytest -q -p no:cacheprovider -n 4 --dist loadfile $own 2>&1 | tail -1
python -m pytest -q -p no:cacheprovider -n 4 --dist loadfile $shared -k "$model and not SEC" 2>&1 | tail -1
