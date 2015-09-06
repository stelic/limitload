#!/bin/bash

this_dir="$(dirname $0)"
source "$this_dir/build_setup"

export LD_LIBRARY_PATH="$this_dir/../src/core:$LD_LIBRARY_PATH"
export PYTHONPATH="$this_dir/..:$PYTHONPATH"
$python_cmd "$this_dir/../src/main.py" "$@"
