"""Check real serialization with an artificial peer; never open a device."""
from pathlib import Path
from hashlib import sha256
import json,os,struct,subprocess,sys
H=Path(__file__).resolve().parent;BASE=H.parent/'stage268-fixed-manual-recovered-communication02'
sys.path.insert(0,str(H));sys.path.append(str(BASE))
import flow_receiver as F
import receipt_receiver as R
assert os.getuid()==os.geteuid()==501
binary=H/'artifacts/emit-check'
cmd=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
    '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(BASE),
    str(H/'flow_journal.c'),str(H/'test_emit.c'),'-o',str(binary)]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
deps=subprocess.check_output(['/usr/bin/otool','-L',str(binary)],text=True);assert 'IOKit.framework'not in deps
rows=[];frames={}
for step in [203,210,0]:
    directory=H/'runs'/('step-'+str(step));directory.mkdir(mode=0o700)
    p=subprocess.run([str(binary),str(directory/'journal.bin'),str(directory/'wire.bin'),str(step)],capture_output=True,text=True)
    assert p.returncode==0,(p.returncode,p.stderr)
    assert not p.stderr
    journal=(directory/'journal.bin').read_bytes();wire=(directory/'wire.bin').read_bytes()
    assert len(journal)==672 and wire==struct.pack('<I',672)+journal
    assert journal[:8]==b'FX3FLOW4' and struct.unpack_from('<I',journal,8)[0]==4
    assert sha256(journal[:640]).digest()==journal[640:]
    returned,known,count,raw=struct.unpack_from('<IIIi',journal,104)
    status=struct.unpack_from('<I',journal,28)[0]
    metadata=F.acquisition_record(journal,11,1,status,returned,raw)
    assert metadata['step']==step and metadata['raw_return']==raw
    frames[step]=journal
    rows.append(dict(case='real-C-serialization-'+str(step),status='PASS',metadata=metadata,
        camera_and_peer_artificial=True,actual_device_API_used=False))
assert F.acquisition_record(frames[203],11,1,8,1,-536870203)['name']!='interface_open'
assert F.acquisition_record(frames[210],11,1,8,1,-536870203)['name']=='interface_open'
def reject(fn):
    try:fn()
    except R.Rejected:return
    raise AssertionError('bad acquisition metadata accepted')
variants=[]
for label,offset,value in [('unknown-step',592,999),('raw-mismatch',596,1),('reserved',600,1)]:
    bad=bytearray(frames[203]);struct.pack_into('<I',bad,offset,value)
    reject(lambda:F.acquisition_record(bytes(bad),11,1,8,1,-536870203));variants.append(label)
reject(lambda:F.acquisition_record(frames[0],11,1,0,1,0));variants.append('success-without-native-step')
reject(lambda:F.acquisition_record(frames[203],11,0,0,0,0));variants.append('before-call-with-substep')
legacy=Path('/private/tmp/fx3-702-recovered-communication-20261101-02/flow-0044.bin').read_bytes()
assert len(legacy)==672 and struct.unpack_from('<I',legacy,24)[0]==11
reject(lambda:F.acquisition_record(legacy,11,1,8,1,-536870203));variants.append('actual-legacy-failure-must-not-invent-substep')
identity=R.Identity(501,os.getpid(),1,2,str(binary),'')
receiver=F.FlowReceiver(identity,bytes(16),'offline-only')
reject(lambda:receiver.accept(legacy));variants.append('legacy-protocol-rejected-by-v4')
rows.append(dict(case='metadata-counterexamples',status='PASS',variants=variants,
    saved_bytes_do_not_recreate_live_origin=True))
receipt=dict(status='ACQUISITION_EVIDENCE_COMPONENT_SERIALIZER_DECODER_PASS',
    scope='real C serializer, real ordinary-user files/fsync, artificial peer and acquisition metadata',
    rows=rows,build_argv=cmd,compile_stderr=p.stderr,binary_sha256=sha256(binary.read_bytes()).hexdigest(),
    dependencies=deps,new_root_or_USB_operations=0,camera_backend_executed=False,
    new_native_entry_or_launch_package=False,whole_controller_integration_proven=False)
with (H/'component-check.json').open('x')as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],real_serializer_cases=3,rejected_variants=len(variants),
    new_root_or_USB_operations=0,whole_controller_integration_proven=False)))
