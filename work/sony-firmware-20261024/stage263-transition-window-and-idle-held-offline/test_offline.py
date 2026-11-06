"""Bounded regression for the actual262 timing failure; no camera access."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
OLD=H.parent/'stage261-fixed-port-association-diagnostic01'
assert len(sys.argv)==2 and sys.argv[1].startswith('attempt') and '/' not in sys.argv[1]
RUN=H/'runs'/sys.argv[1];RUN.mkdir(mode=0o700)
sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('timing263_decoder',H/'flow_receiver.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
R=F.R
identity=R.Identity(uid=os.geteuid(),pid=1234,sec=100,usec=200,
                    path='offline-provider-no-live-origin',image_sha256='0'*64)
nonce=b'N'*16
rows=[]
raws={}
for scenario,name in [(0,'service-at-3200ms-return-at-3600ms'),(1,'no-service-in-five-seconds'),
                      (2,'wrong-physical-anchor'),(3,'overall-deadline-still-three-seconds')]:
    directory=RUN/name;directory.mkdir(mode=0o700)
    p=subprocess.run([str(H/'artifacts/timing-fixture'),str(scenario),str(directory/'raw-flow.bin')],
                     capture_output=True,text=True,timeout=15)
    (directory/'stdout.txt').write_text(p.stdout);(directory/'stderr.txt').write_text(p.stderr)
    assert p.returncode==0 and not p.stderr,(scenario,p.returncode,p.stdout,p.stderr)
    result=json.loads(p.stdout)
    raw=(directory/'raw-flow.bin').read_bytes();assert len(raw)%672==0
    frames=[raw[i:i+672] for i in range(0,len(raw),672)];raws[scenario]=frames
    receiver=F.FlowReceiver(identity,nonce,'offline-timing-263')
    for frame in frames:receiver.accept(frame)
    assert receiver.terminal
    assert receiver.complete==(scenario==0)
    if scenario==0:
        assert result['virtual_elapsed_ms']==6800 and receiver.body_bytes==88
        samples=[struct.unpack_from('<I',f,548)[0] for f in frames]
        assert max(samples)>20
    else:
        assert result['opens']==result['STOPs']==0 and result['flow_object_classifier']==0
        assert not any(pid==0x0336 for pid,op in receiver.calls)
        if scenario==1:assert result['virtual_elapsed_ms']==5000
        if scenario==3:assert result['virtual_elapsed_ms']==3000
    rows.append(dict(case=name,status='PASS',frames=len(frames),result=result,
                     virtual_native_provider=True,live_peer_origin=False,actual_camera=False))

def reject_rehashed(frames,index,edit):
    altered=[bytearray(f) for f in frames];edit(altered[index]);previous=bytes(32)
    for f in altered:
        f[608:640]=previous;f[640:]=hashlib.sha256(f[:640]).digest();previous=bytes(f[640:])
    receiver=F.FlowReceiver(identity,nonce,'offline-timing-263')
    try:
        for f in altered:receiver.accept(bytes(f))
    except R.Rejected:return
    raise AssertionError('decoder accepted a rehashed out-of-bounds witness')

arm=next(i for i,f in enumerate(raws[0]) if struct.unpack_from('<I',f,24)[0]==60)
def over_window(f):
    armed=struct.unpack_from('<Q',f,512)[0];struct.pack_into('<Q',f,520,armed+5_000_000_001)
reject_rehashed(raws[0],arm,over_window)
last_sample=max(i for i,f in enumerate(raws[1]) if struct.unpack_from('<I',f,24)[0]==61)
reject_rehashed(raws[1],last_sample,lambda f:struct.pack_into('<I',f,548,51))
rows.append(dict(case='decoder-denies-window-over-5s-and-sample51-even-after-rehash',status='PASS',variants=2))

cmd=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror',
     '-Wno-deprecated-declarations','-fsanitize=address,undefined','-fno-sanitize-recover=all',
     '-DFX3_ENTRY_FIXTURE','-I',str(OLD),str(H/'global_unknown_fixture.c'),
     str(OLD/'global_guard.c'),str(OLD/'entry_support.c'),str(OLD/'owner_ipc.c'),
     '-o',str(H/'artifacts/unknown-fixture')]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
deps=subprocess.check_output(['/usr/bin/otool','-L',str(H/'artifacts/unknown-fixture')],text=True)
assert 'IOKit.framework' not in deps
directory=RUN/'unknown-after-child-exit';directory.mkdir(mode=0o700)
p=subprocess.run([str(H/'artifacts/unknown-fixture'),str(directory/'test-only.journal')],capture_output=True,text=True,timeout=10)
assert p.returncode==0 and not p.stderr,(p.returncode,p.stdout,p.stderr)
(directory/'stdout.txt').write_text(p.stdout)
rows.append(dict(case='host-only-child-exit-does-not-clear-durable-UNKNOWN',status='PASS',
                 compile_argv=cmd,dependencies=deps,journal_bytes=(directory/'test-only.journal').stat().st_size))

receipt=dict(status='OFFLINE_TARGETED_REGRESSIONS_PASS',checks=len(rows),rows=rows,
             run_directory=str(RUN),
             camera_recovery_proven=False,cooperative_exit_integrated=False,
             native_helper_built_or_run=False,new_root_or_USB_operations=0)
with (H/'test-receipt.json').open('x') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='rows'}))
