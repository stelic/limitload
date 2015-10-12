#!/bin/bash

script_dir="$(dirname $0 | xargs readlink -f)"
# ...need absolute directory because cwd is changed below.
source "$script_dir/build_setup"

pack_dir="$1"
if test -z "$pack_dir"; then
    echo "*** Missing argument: source package directory path."
    exit 1
fi

domain_base=limload

pack_name=$(basename $pack_dir)
pack_type=$(basename $(dirname $pack_dir))

domain=$domain_base-$pack_name
rev_dir=../../..
domain_dir="$pack_dir/$rev_dir/language/po/$domain"
mkdir -p "$domain_dir"
cd "$domain_dir"
rev_pack_dir=$rev_dir/src/$pack_type/$pack_name
$python_cmd "$script_dir/extract_srcpack_pot.py" "$rev_pack_dir" $domain.pot
