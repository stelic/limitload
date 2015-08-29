#!/bin/bash

script_dir=$(dirname $0)
source "$script_dir/build_setup"

root_dir=$(dirname "$script_dir")
panda_root_dir=$(dirname "$panda_lib_dir" | sed 's#^\(.\):#/\1#')
python_root_dir=$(dirname "$python_lib_dir" | sed 's#^\(.\):#/\1#')

export PYTHONPATH="$root_dir$envsep$PYTHONPATH"
$python_cmd -u "$script_dir/pack_zip_all.py" \
    $build_env "$root_dir/../pack" \
    "$root_dir" "$panda_root_dir" "$python_root_dir"

