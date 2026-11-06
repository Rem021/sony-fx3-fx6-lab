#!/usr/bin/env python3
"""Preserve the first build and add the exported function's required prototype."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'work/libusb-1.0.30/libusb/os/darwin_usb.c'


def main():
    receipt=HERE/'private-source-patch.json'
    old=json.loads(receipt.read_text());raw=SOURCE.read_bytes()
    assert sha256(raw).hexdigest()==old['patched_sha256']
    text=raw.decode();needle='int API_EXPORTED libusb_fx3_set_target(uint32_t location) {'
    assert text.count(needle)==1
    text=text.replace(needle,'int API_EXPORTED libusb_fx3_set_target(uint32_t location);\n'+needle,1)
    history=HERE/'attempt-initial-missing-prototype';history.mkdir(exist_ok=False)
    (history/'darwin_usb-patched-before-prototype.c').write_bytes(raw)
    receipt.rename(history/receipt.name)
    for path in HERE.glob('build-step*.log'):path.rename(history/path.name)
    (HERE/'work/native-build').rename(HERE/'work/native-build-initial')
    SOURCE.write_text(text)
    updated={**old,'patched_sha256':sha256(text.encode()).hexdigest(),
             'prototype_fix_previous_sha256':old['patched_sha256'],
             'prototype_fix_script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
             'strict_warning_policy_preserved':True,'initial_compile_failure_preserved':True}
    with receipt.open('x') as h:json.dump(updated,h,ensure_ascii=False,indent=2);h.write('\n')
    print('Added exported prototype; preserved initial compile failure; no device operations')


if __name__=='__main__':main()
