"""Real unprivileged helper/IPC/legacy-journal integration with fake camera."""
from pathlib import Path
from hashlib import sha256
import json,os,struct,subprocess,sys
sys.dont_write_bytecode=True
import supervisor as S
import receipt_receiver as R
H=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1].startswith('attempt') and '/' not in sys.argv[1]
prefix=sys.argv[1]+'-';base=H.parent/'stage264-cooperative-idle-held-exit'
cmd=['/usr/bin/xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
     '-fsanitize=address,undefined','-fno-sanitize-recover=all','-DFX3_ENTRY_FIXTURE','-I',str(H),
     str(H/'recovery_seed.c'),str(base/'global_guard.c'),str(base/'entry_support.c'),str(base/'owner_ipc.c'),
     '-o',str(H/'artifacts/recovery-seed')]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
rows=[];completed=None
cases=[('manual-full-flow',0,67108864,False,'HOST_RETURN_CONTROLLED_PORT_ASSOCIATION'),
       ('manual-idle-exit',0,16384,False,'HOST_IDLE_EXIT_CAMERA_STATE_UNKNOWN'),
       ('wrong-cache-port',2,67108864,False,'DENIED_BEFORE_OWNER_ACTIONS'),
       ('mounted-cache',6,67108864,False,'DENIED_BEFORE_OWNER_ACTIONS'),
       ('stale-cache',4,67108864,False,'DENIED_BEFORE_OWNER_ACTIONS'),
       ('old-owner-still-live',0,67108864,True,'DENIED_BEFORE_OWNER_ACTIONS'),
       ('interrupted-after-recovery-record',100,67108864,False,'DENIED_OWNER_NOT_STARTED_RECOVERY_TAIL_RETAINED')]
for name,variant,option,keep_live,expected in cases:
    seed_dir=H/'runs'/(prefix+name+'-seed');seed_dir.mkdir(mode=0o700)
    guard=seed_dir/'old.journal';spec=seed_dir/'recovery.bin'
    seed=subprocess.Popen([str(H/'artifacts/recovery-seed'),str(guard),str(spec),str(variant)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert seed.stdout.readline()=='ready\n'
    if not keep_live:
        seed.stdin.write('x');seed.stdin.flush();assert seed.wait(timeout=3)==0
    before=guard.read_bytes();assert len(before)==256
    j=S.Job.fixture(name=prefix+name,fixture_option=option,guard=guard,recovery_spec=spec)
    try:
        value=j.wait(8);assert value['status']==expected,value
        assert value['helper_terminal_observed'] and not value['new_trial_authorized']
        assert j.receipt is not None;stamp=j.receipt['manual_recovery'];after=guard.read_bytes()
        assert after[:len(before)]==before and j.runner.wait(timeout=3)==0
        if expected.startswith('HOST_'):
            assert stamp['stage']==2 and len(after)==4*256
            assert stamp['prior_tail_hash']==before[-32:].hex() and stamp['recovered_hash']==after[256+224:512].hex()
            assert stamp['source_node']==j.flow_state.source_node==100
            assert struct.unpack_from('<I',after,256+20)[0]==4 and struct.unpack_from('<I',after,512+20)[0]==1
            assert struct.unpack_from('<I',after,768+20)[0]==3
            completed=(j.directory,j.verified.identity,j.frame.nonce,stamp)
        elif variant==100:
            assert stamp['stage']==1 and not j.receipt['owner_ran'] and not j.flow_frames and len(after)==512
            assert struct.unpack_from('<I',after,256+20)[0]==4
        else:
            assert stamp['stage']==0 and not j.receipt['owner_ran'] and not j.flow_frames and after==before
        rows.append(dict(case=name,status='PASS',observed_status=value['status'],manual_stage=stamp['stage'],
                         frames=len(j.flow_frames),kernel_peer_checked=True,device_and_cache_artificial=True))
    finally:
        if j.runner.poll() is None:j.request_stop();j.frame.fixture_gate(2)
        j.runner.wait(timeout=5);assert j.ipc.probe(j.verified.identity.pid) is None
        j.out.flush();j.err.flush();err=(j.directory/'runner-stderr.txt').read_bytes()+(j.directory/'relay-stdout.txt').read_bytes()
        assert b'ERROR: AddressSanitizer' not in err and b'runtime error:' not in err
        j.close_observer()
        if seed.poll() is None:seed.stdin.write('x');seed.stdin.flush();assert seed.wait(timeout=3)==0
        assert not seed.stderr.read()

directory,identity,nonce,stamp=completed
original=(directory/'private-record.bin').read_bytes()
for name,offset,data in [('missing-prior-hash',896,bytes(32)),('stage-out-of-range',892,struct.pack('<I',3)),
                         ('source-zero',960,bytes(8)),('reserved',980,struct.pack('<I',1))]:
    bad=bytearray(original);bad[offset:offset+len(data)]=data;bad[992:]=sha256(bad[:992]).digest()
    try:R.decode_record(bytes(bad),identity,nonce)
    except R.Rejected:pass
    else:raise AssertionError(name+' accepted')
rows.append(dict(case='saved-byte-manual-stamp-forgeries-rejected',status='PASS',variants=4,live_origin_recreated=False))
result=dict(status='MANUAL_RECOVERY_ENTRY_PRIVATE_STAMP_AND_FLOW_OWN_PROCESS_PASS',checks=len(rows),rows=rows,
            seed_compile_argv=cmd,native_helper_executed=False,actual_root_journal_modified=False,
            new_root_or_USB_operations=0,new_camera_trial_authorized=False)
with (H/'test-receipt.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('rows','seed_compile_argv')}))
