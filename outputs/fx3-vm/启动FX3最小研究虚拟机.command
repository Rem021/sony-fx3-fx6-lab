#!/bin/zsh
set -eu
task_dir="${0:A:h}"
exec /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 "$task_dir/run_probe.py" --profile minimal-linux --seconds 12
