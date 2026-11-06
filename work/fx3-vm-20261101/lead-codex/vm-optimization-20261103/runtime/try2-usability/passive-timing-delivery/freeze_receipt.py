#!/usr/bin/env python3
"""Freeze paths/hashes for offline review; does not access QEMU or locks."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
USABILITY = HERE.parent
MSS = USABILITY / 'mss-all-key-contrast'
FILES = [
    HERE / 'build_candidate.py', HERE / 'pending_visual_v20.py',
    HERE / 'run_trial_v20_passive_timing.py', HERE / 'trial_web_v20_passive_timing.py',
    HERE / 'test_v20_offline.py', HERE / 'host-v19-to-v20.diff',
    HERE / 'web-v3-to-v20.diff', MSS / 'run_trial_v19_mss_key_contrast_preinput_stop.py',
    MSS / 'passive-timing-next/src/fx3-rm-empty-provider-v8-long-use-timing.c',
    MSS / 'passive-timing-next/src/fx3-preset-context-v6-save102-timing.c',
    MSS / 'passive-timing-next/src/fx3-osd-headless-v7-observe102-timing.c',
    MSS / 'passive-timing-next/build/rm-timing.so',
    MSS / 'passive-timing-next/build/ap-timing.so',
    MSS / 'passive-timing-next/build/osd-timing.so',
    HERE / 'vmopt-20261103-try2-passive-timing-v4/candidate.json',
    HERE / 'vmopt-20261103-try2-passive-timing-v4/guest.cpio',
    HERE / 'vmopt-20261103-try2-passive-timing-v4/guest.dtb',
    HERE / 'vmopt-20261103-try2-passive-timing-v4/build-receipt.json',
    HERE / 'vmopt-20261103-try2-passive-timing-v4/cpio-audit.json',
]

def sha(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()

rows = [{'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size} for path in FILES]
receipt = {
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'offline_only_not_guest_validated_not_deployed',
    'volume_uuid_verified': 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B',
    'QEMU_started': False, 'default_entry_changed': False,
    'offline_fixture_tests': 11, 'offline_fixture_result': 'pass',
    'python_compile': 'pass', 'runner_help': 'pass',
    'cpio_audit_safe_to_unpack': True,
    'files': rows,
}
(HERE / 'OFFLINE-RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'files': len(rows), 'candidate_sha256': rows[-5]['sha256'], 'QEMU_started': False}))
