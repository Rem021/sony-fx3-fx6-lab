#!/usr/bin/env python3
"""Replay the sealed153 core checks against ABI2, plus pre-stop/control-ABI cases."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parents[1]


def main():
    prior=HERE.parent/'stage153-Mac-owned-interface-trial'
    raw=(prior/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='27fbc16f5e22e122de6bb144116be44454f5a52b5c07d9eef2361ae681f57460'
    source=prior/'test_owner_core.py'
    pin=next(m for m in json.loads(raw)['files'] if m['path']==source.relative_to(ROOT).as_posix())
    original=source.read_bytes();assert sha256(original).hexdigest()==pin['sha256']
    text=original.decode().replace("out = HERE / 'run-owner-fixtures'","out = HERE / 'run-core-regression'")
    text=text.replace('0x46495833','0x46495834').replace('b.Config(abi=1,','b.Config(abi=2,')
    text=text.replace("('abi', 2)","('abi', 3)")
    text=text.replace('def case(name, fail=0, option=0, late=0, change=None):','def case(name, fail=0, option=0, late=0, change=None, stop=False, control_abi=2):')
    text=text.replace('rc = run(C.byref(config), C.byref(result))','control = b.Control(abi=control_abi, stop_requested=1 if stop else 0)\n        rc = run(C.byref(config), C.byref(result), C.byref(control))')
    text=text.replace('    class Poison:',
        "    rc,calls,r=case('stop_before_any_provider_call',stop=True)\n    assert rc==2 and sum(calls.values())==0\n"
        "    rc,calls,r=case('invalid_control_ABI',control_abi=1)\n    assert rc==3 and sum(calls.values())==0\n    class Poison:")
    text=text.replace("'test_owner_core.py'","'test_core_regression.py'")
    with (HERE/'test_core_regression.py').open('x') as handle:handle.write(text)
    with (HERE/'regression-derivation.json').open('x') as handle:json.dump({'source':pin,
        'output_sha256':sha256(text.encode()).hexdigest(),'ABI2_stop_and_control_type_checks_added':True},handle,indent=2)
    print(json.dumps({'prepared':'test_core_regression.py','downloaded_or_device_code_executed':False}))


if __name__=='__main__':main()
