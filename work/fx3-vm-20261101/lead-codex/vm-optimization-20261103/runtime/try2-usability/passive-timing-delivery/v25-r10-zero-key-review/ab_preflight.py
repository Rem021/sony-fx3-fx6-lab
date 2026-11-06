#!/usr/bin/env python3
"""Read-only source, volume and occupancy gate for a future A/B review."""
import fcntl
import json
import plistlib
import re
import subprocess
from pathlib import Path
from ab_observer import ARMS, HOST, sha, source_check

UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
source_check()
root = Path('/Volumes/KAFU2T/AI/Projects/Mac')
vol = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
if vol.get('VolumeUUID') != UUID:
    raise RuntimeError('wrong external volume UUID')
ps = subprocess.check_output(['ps','-axo','pid=,command='], text=True)
busy = [line.strip() for line in ps.splitlines()
        if re.search(r'/qemu-gpio5-[0-9a-f]+|[/ ]run_trial_v25_diag_r3\.py(?: |$)',line)]
if busy:
    raise RuntimeError('existing VM/runner: '+repr(busy[:8]))
for rel in ('outputs/fx3-vm/.run.lock',
            'work/fx3-vm-20261101/menu-repair-01/runtime/.run.lock'):
    with (root/rel).open('rb') as f:
        try: fcntl.flock(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError('run lock occupied: '+rel) from exc
        finally:
            try: fcntl.flock(f, fcntl.LOCK_UN)
            except OSError: pass
for arm, pin in ARMS.items():
    candidate = (HOST.parent/'v25-r4-postmortem-host/vmopt-20261104-v25-procdiag-r4e/candidate.json'
                 if arm == 'B' else HOST.parent/'v25-menu-osd-diagnostic-r3/vmopt-20261104-v25-menu-osd-diagnostic-r3/candidate.json')
    if sha(candidate) != pin['candidate']:
        raise RuntimeError('candidate mismatch '+arm)
    manifest = json.loads(candidate.read_text())
    if sha(manifest['initrd']['path']) != pin['cpio']:
        raise RuntimeError('CPIO mismatch '+arm)
    print(arm, 'candidate', pin['candidate'], 'CPIO', pin['cpio'])
print('PREFLIGHT_OK UUID, both locks free, no QEMU/runner, frozen host and both arm pins')
