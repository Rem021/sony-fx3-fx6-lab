#!/bin/sh
# Local, temporary disassembler/emulator dependencies; no firmware execution.
set -eu
cd "$(dirname "$0")"
python3 -m pip install --disable-pip-version-check --no-input --target .vendor 'capstone==5.0.6' 'unicorn==2.1.4'
