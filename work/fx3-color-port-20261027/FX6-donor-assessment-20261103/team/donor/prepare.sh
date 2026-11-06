#!/bin/sh
# Recreate temporary pinned parser dependencies inside this directory.
set -eu
cd "$(dirname "$0")"
pin=3955d7890fc38daf942bb52827599bfe35de4a14
url="https://github.com/DavidBuchanan314/fwtool.py/archive/$pin.tar.gz"
curl -fLsS --max-time 120 "$url" -o fwtool-upstream.tar.gz
printf '%s  %s\n' '6abc19ad21aedaa90bf52cc16ff635bc78a209af377ac95e00a445c27a580fb3' fwtool-upstream.tar.gz | shasum -a 256 -c -
tar -xzf fwtool-upstream.tar.gz
python3 -m pip install --disable-pip-version-check --no-input --target .vendor 'pyelftools==0.33' 'pyfatfs==1.1.0' 'setuptools==70.0.0'
