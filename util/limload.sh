#!/bin/sh

this_dir="$(dirname $0)"
export LD_LIBRARY_PATH="$this_dir/../src/core:$LD_LIBRARY_PATH"
export PYTHONPATH="$this_dir/..:$PYTHONPATH"
python "$this_dir/../src/main.py" "$@"
