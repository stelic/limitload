#!/bin/bash

script_dir=`dirname $0`

domain_base=limload

domain_dir="$script_dir/../language/po/$domain_base"
mkdir -p "$domain_dir"
cd "$domain_dir"
rev_dir=../../..
:>file-list
find $rev_dir/src -maxdepth 1 -iname \*.py | sort >>file-list
find $rev_dir/src/core -iname \*.py | sort >>file-list
find $rev_dir/src/blocks -iname \*.py | sort >>file-list
xgettext --files-from=file-list --no-wrap -o "$domain_base.pot" \
    -k_: -kn_:1,2 -kp_:1c,2 -kpn_:1c,2,3 -cTRNOTE:
rm file-list
