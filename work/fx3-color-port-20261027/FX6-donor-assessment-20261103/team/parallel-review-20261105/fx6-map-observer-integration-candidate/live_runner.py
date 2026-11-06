#!/usr/bin/env python3
"""Adapter: frozen r6 HostRunner + new CPIO/hash + framed provider."""
import hashlib,time,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import framed_provider as FP
import decode_snapshot as D
R6=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-backup-read-observer-candidate')
NEW_CPIO=HERE/'work/fx6-map-observer-grmreal46.cpio'
NEW_SHA='9d4f255b0a3995b0e056e210ae4d27c8129e2c853b35904a688b6ffe149529ae'
NEW_BYTES=453306948
def _sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def _remaining(deadline):
 if deadline is None:return 150.0
 for name in ('remaining_observation','remaining_total'):
  try:return max(0.0,float(getattr(deadline,name)()))
  except Exception:pass
 return 0.0
def _wait_mapping(provider,serial,deadline):
 last='none'; serial=Path(serial)
 while True:
  raw=serial.read_bytes()
  # Stream frontier: only complete newline-terminated lines may be semantically
  # parsed.  A partial tail is held; no prior frame is returned while a tail is
  # present.  Complete malformed fields/nested BEGIN/identity changes reject.
  lines=raw.split(b'\n')
  complete=b'\n'.join(lines[:-1])+ (b'\n' if len(lines)>1 else b'')
  tail=lines[-1]
  try:
   text=complete.decode('utf-8','replace')
   if complete:
    try:return provider.select(text) if not tail else _raise_if_complete_valid(text,tail)
    except D.ProtocolError as e:
     msg=str(e)
     if msg in ('no complete frame','missing END'):last=msg
     else:raise
  except UnicodeDecodeError:raise
  rem=_remaining(deadline)
  if rem<=0:raise TimeoutError('no complete framed map before deadline: '+last)
  time.sleep(min(0.05,rem))
def _raise_if_complete_valid(complete,tail):
 # A complete frame exists, but a nonempty unterminated tail may be the next
 # BEGIN.  Do not accept the older frame; wait for frontier.
 raise D.ProtocolError('no complete frame')
def build_runner(root,deps_factory=None):
 sys.path.insert(0,str(R6/'observer'))
 import host_runner
 # Full frozen artifact gate first, while baseline target still points at 3a08.
 base=host_runner.baseline_binding.verify_artifacts()
 if _sha(NEW_CPIO)!=NEW_SHA or NEW_CPIO.stat().st_size!=NEW_BYTES:raise RuntimeError('new CPIO preflight mismatch')
 host_runner.baseline_binding.TARGET=NEW_CPIO
 host_runner.baseline_binding.TARGET_SHA=NEW_SHA
 host_runner.baseline_binding.TARGET_BYTES=NEW_BYTES
 deps=deps_factory() if deps_factory is not None else host_runner.real_deps(root)
 provider=FP.FramedProvider(cpio_path=None,cpio_sha=NEW_SHA)  # CPIO checked once here, not each poll
 def verify():
  if _sha(NEW_CPIO)!=NEW_SHA or NEW_CPIO.stat().st_size!=NEW_BYTES:raise RuntimeError('new CPIO preflight drift')
  return {**base,'new_cpio_sha256':NEW_SHA,'new_cpio_bytes':NEW_BYTES}
 def mapping(serial,deadline=None):return _wait_mapping(provider,serial,deadline)
 deps['verify_artifacts']=verify
 deps['mapping_provider']=mapping
 deps['stop_only']=True
 return host_runner.HostRunner(deps)
