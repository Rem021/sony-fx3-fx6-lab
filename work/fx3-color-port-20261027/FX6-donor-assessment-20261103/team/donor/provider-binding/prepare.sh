#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m pip install --disable-pip-version-check --quiet --target .vendor capstone==5.0.6 pyelftools==0.32 unicorn==2.1.4
