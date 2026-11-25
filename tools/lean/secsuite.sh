#!/bin/bash
# Run uslib's SEC modules (which read the S twins) in a tree, writing JUnit XML.
#   tools/lean/secsuite.sh <tree> <junit.xml>
cd "$1/lifelib/libraries/uslib/tests" || exit 2
python -m pytest -q -p no:cacheprovider -n 2 --dist loadfile $(ls test_*_sec.py) test_sec_support.py --junitxml="$2" 2>&1 | tail -1
