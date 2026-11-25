#!/bin/bash
# patches.sh REPO BASE OUTDIR : format-patch BASE..HEAD, author/date header and trailer lines removed
set -e; R=$1; B=$2; O=$3; mkdir -p $O; T=$(mktemp -d)
git -C $R format-patch -q --no-signature --zero-commit -o $T $B
for f in $T/*.patch; do
  sed -E '/^From: /d; /^Date: /d; /^(Co-Authored-By|Signed-off-by|[A-Za-z]+-Session|Reviewed-by):/Id' $f > $O/$(basename $f)
done
rm -rf $T; ls $O
