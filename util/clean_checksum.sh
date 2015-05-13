#!/bin/bash

set -e

sumpath=$1
if test -z "$sumpath"; then
    echo "usage: $0 OUTFILE"
    exit 1
fi

echo "===== Cleaning directory..."
make clean >/dev/null

echo "===== Calculating checksums..."
rm -f $sumpath
find -type f -print0 \
| grep -zZv '/cache/\|/save/\|/log/\|/build_setup$\|/config/.*.ini$\|\./_' \
| sort -z \
| xargs -0 md5sum -b \
> $sumpath

echo "===== Checksums written to: $sumpath"
