#!/bin/bash
# Run one library's model tests (each product's own module and the shared convention
# modules; not the *_sec.py modules) in a tree, writing JUnit XML.
#   tools/lean/suite.sh <tree> <lib> <junit.xml>
tree=$1; lib=$2; xml=$3
cd "$tree/lifelib/libraries/$lib/tests" || exit 2
files=$(ls test_*.py | grep -v "_sec.py$" | grep -v "test_sec_support.py\|test_cython_toolchain.py")
python -m pytest -q -p no:cacheprovider -n 4 --dist loadfile $files --junitxml="$xml" 2>&1 | tail -1
