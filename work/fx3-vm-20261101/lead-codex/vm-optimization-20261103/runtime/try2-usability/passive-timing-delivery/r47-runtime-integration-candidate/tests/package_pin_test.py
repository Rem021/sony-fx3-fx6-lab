#!/usr/bin/env python3
"""Offline proof that the reused r42 package/CPIO/DTB pins are unchanged; no copy/write."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'run-inputs/r47-offline-closed-loop'
spec = importlib.util.spec_from_file_location('r47_r35', HERE / 'r35_package_selection.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sel = m.verify_package(RUN)
value = {'schema': 'fx3-r47-package-pin-v1', 'offline': True, 'browser': False, 'server': False,
         'VM': False, 'QMP': False, 'guest': False, 'copied_or_written_package': False,
         'selection': sel,
         'package_candidate_sha256': hashlib.sha256((m.PACKAGE / 'candidate.json').read_bytes()).hexdigest(),
         'package_cpio_sha256': hashlib.sha256((m.PACKAGE / 'guest.cpio').read_bytes()).hexdigest()}
assert sel['candidate_sha256'] == '857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806'
assert sel['initrd_sha256'] == '59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63'
assert sel['initrd_bytes'] == 453213884
assert sel['profile'] == 'r47-runtime-integration-60s' and sel['label'] == 'v47runtime-n64-r47'
(HERE / 'receipts/package-pin.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'passed': True, 'profile': sel['profile'], 'candidate': sel['candidate_sha256'],
                  'cpio': sel['initrd_sha256'], 'receipt': str(HERE / 'receipts/package-pin.json')}))
