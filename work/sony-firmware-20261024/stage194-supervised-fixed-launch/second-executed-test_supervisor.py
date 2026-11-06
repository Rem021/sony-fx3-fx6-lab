"""Execute own unprivileged fake owners and shell wrappers; never sudo/native."""
from pathlib import Path
from hashlib import sha256
from dataclasses import replace
from contextlib import contextmanager
import json,os,secrets,struct,subprocess,time,traceback
import controller_ipc as I
import fixed_launch as P
import receipt_receiver as R
import supervisor as S
HERE=S.HERE;results=[];template=None;proof=None;nonce=None

def reject(fn,types=(R.Rejected,OSError)):
    try:fn()
    except types:return
    raise AssertionError('invalid input accepted')

@contextmanager
def job(**kw):
    j=S.Job.fixture(**kw)
    try:yield j
    finally:
        if j.runner.poll() is None:
            j.request_stop();j.frame.fixture_gate(2) # own fake-call test gates only
        j.runner.wait(timeout=4)
        if j.relay is not j.runner:j.relay.wait(timeout=2)
        j.out.flush();j.err.flush()
        err=(j.directory/'runner-stderr.txt').read_bytes()
        logs=(j.directory/'relay-stdout.txt').read_bytes() if (j.directory/'relay-stdout.txt').exists() else b''
        assert b'ERROR: AddressSanitizer' not in err+logs and b'runtime error:' not in err+logs,(err,logs)
        j.close_observer()

def full_launch():
    global template,proof,nonce
    with job() as j:
        value=j.wait();assert value['status']=='HOST_RETURN_OBSERVED',value
        assert j.verified.identity.pid!=j.relay.pid
        assert len(j.responses)==2 and j.hello['image_sha256']==j.expected_digest
        assert j.receipt['transport_peer_verified'] and j.receipt['native_return']==0
        assert not value['automatic_retry'] and not value['physical_camera_acceptance']
        g=j.frame.snapshot();assert j.entry_ack_ns<=g.started_ns<j.entry_ack_ns+500_000_000
        assert (j.directory/'installed/entry.once').is_file()
        template=(j.directory/'live-self-image.bin').read_bytes();proof=j.verified;nonce=j.frame.nonce
        (HERE/'template-hello.bin').write_bytes(template)
        S.put(HERE/'template-hello-proof.json',{'identity':proof.identity.__dict__,'mode':proof.mode,'expected_digest':proof.expected_image_sha256,'nonce':nonce.hex()})

def relay_not_owner():
    with job(block=7,early_relay=True) as j:
        value=j.wait(.15);assert value['relay_returncode']==0 and value['status']=='OWNER_ALIVE_UNRESOLVED',value
        pid=j.verified.identity.pid;assert pid!=j.relay.pid and j.ipc.probe(pid) is not None
        before=(j.directory/'installed/entry.once').read_bytes()
        j.wait(.1);assert j.verified.identity.pid==pid and (j.directory/'installed/entry.once').read_bytes()==before
        j.frame.fixture_gate(1)
        assert j.wait()['status']=='HOST_RETURN_OBSERVED'

def observation_timeout_same_pending_owner():
    with job(block=2) as j:
        first=j.wait(.1);assert first['status']=='OWNER_ALIVE_UNRESOLVED',first
        pid=j.verified.identity.pid
        second=j.wait(.08);assert second['status']=='OWNER_ALIVE_UNRESOLVED' and j.ipc.probe(pid) is not None
        assert j.receipt is None and j.verified.identity.pid==pid
        j.request_stop();j.frame.fixture_gate(1)
        assert j.wait()['status']=='HOST_ABORT_RETURN_OBSERVED'

def retained_and_cross_instance_fence():
    with job(vendor_fixture=True) as a:
        value=a.wait();assert value['status']=='OWNER_RETAINED',value
        pid=a.verified.identity.pid
        assert a.receipt['phase']=='HELD' and a.runner.poll() is None
        os.pwrite(a.frame.fd,struct.pack('<I',1),a.ipc.grant_offset+I.Grant.completed.offset)
        with job(guard=a.guard) as b:
            value=b.wait();assert value['status']=='DENIED_BEFORE_OWNER_ACTIONS',value
            assert b.receipt['global_guard_result']==1 and not b.receipt['owner_ran']
        assert a.ipc.probe(pid) is not None and a.wait(.04)['status']=='OWNER_RETAINED'

def install_digest_failure_and_forged_relay():
    with job(bad_digest=True) as j:
        value=j.wait();assert value['status']=='UNKNOWN_ENTRY_NOT_VERIFIED',value
        assert j.verified is None and j.runner.poll()==78
        assert not (j.directory/'installed/entry.once').exists()
        (j.directory/'relay-stdout.txt').write_text('{"native_return":0,"physical_camera_acceptance":true}\n')
        (j.directory/'terminal-marker.json').write_text('{"relay_returncode":0}\n')
        assert j.step()['status']=='UNKNOWN_ENTRY_NOT_VERIFIED'

def wrong_expected_helper_digest():
    with job() as j:
        j.expected_digest='0'*64
        value=j.wait();assert value['status']=='UNKNOWN_OBSERVER_ERROR',value
        assert j.verified is None and not j.guard.exists()

def source_hazards():
    directory=HERE/'runs'/('source-'+secrets.token_hex(4));directory.mkdir(mode=0o700)
    source=Path(I.build()['builds']['fixture']['path']);digest=sha256(source.read_bytes()).hexdigest()
    link=directory/'symbolic';link.symlink_to(source)
    reject(lambda:P.private_copy(link,digest,directory))
    fifo=directory/'fifo';os.mkfifo(fifo,0o600);reject(lambda:P.private_copy(fifo,digest,directory))
    regular=directory/'regular';regular.write_bytes(source.read_bytes());os.link(regular,directory/'second')
    reject(lambda:P.private_copy(regular,digest,directory))
    assert not (directory/'source-helper').exists()

def one_attempt_wrapper():
    with job() as j:
        assert j.wait()['status']=='HOST_RETURN_OBSERVED'
        j.runner.wait(timeout=2);before=j.guard.read_bytes()
        r=subprocess.run(['/bin/sh',str(j.command)],stdin=subprocess.DEVNULL,capture_output=True,timeout=2)
        assert r.returncode and j.guard.read_bytes()==before
        assert j.ipc.probe(j.verified.identity.pid) is None
        (j.directory/'replay-stderr.txt').write_bytes(r.stderr)

def native_render_only():
    command,body=P.render_native('a'*32)
    assert '/usr/bin/sudo -- ' in command and str(P.ROOT_DIR/'helper') in body
    assert R.GRANT_ID in command and 'shasum -a 256' in body
    checked=subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True,timeout=2)
    assert checked.returncode==0,checked.stderr
    reject(lambda:P.native_authority({'authorization':{'Mac_owner_trial_authorized':True},'prepared_first_device_trial':{'Mac_owner_trial_released':True}}))
    (HERE/'native-render-only.command.txt').write_text(command)
    assert '#define FX3_NATIVE_RELEASED 0' in (HERE/'entry_target.h').read_text()

def recorded_file_not_live_authentication():
    with job() as j:
        assert j.wait()['status']=='HOST_RETURN_OBSERVED'
        me=j.ipc.probe(os.getpid());assert me
        (j.directory/'verified-helper.json').write_text(json.dumps({'identity':me.__dict__,'authenticated_completion':True}))
        (j.directory/'private-record.json').write_text('{"transport_peer_verified":true,"native_return":0}')
        value=S.recorded_observation(j.directory)
        assert value['status']=='UNKNOWN_RECORDED_CONTEXT' and not value['authenticated_completion']
        assert value['current_process_matches_untrusted_record'] and not value['automatic_retry']

def public_report_truncation_while_profile_pending():
    with job(block=8) as j:
        value=j.wait(.12);assert value['status']=='OWNER_ALIVE_UNRESOLVED',value
        os.ftruncate(j.frame.fd,0);time.sleep(.05);assert j.runner.poll() is None
        j.frame.fixture_gate(1)
        value=j.wait();assert value['status']=='HOST_ABORT_RETURN_OBSERVED',value
        assert j.receipt['frame_io_failed']

def hello_ack_timeout_no_owner():
    with job() as j:
        def no_ack(data):j.hello=j.receiver.accept_hello(data)
        j._hello=no_ack
        value=j.wait();assert value['status']=='DENIED_BEFORE_OWNER_ACTIONS',value
        assert not j.receipt['owner_ran'] and not j.guard.exists()

def stop_between_hello_and_ack():
    with job() as j:
        def cancel(data):
            j.hello=j.receiver.accept_hello(data);j.frame.stop();j.receiver.acknowledge()
        j._hello=cancel
        value=j.wait();assert value['status']=='DENIED_BEFORE_OWNER_ACTIONS',value
        assert not j.receipt['owner_ran'] and not j.guard.exists()

def corrupted_self_image_hello_no_ack():
    with job() as j:
        original=j._hello
        def corrupt(data):
            data=bytearray(data);data[88]^=1;data[128:]=sha256(data[:128]).digest();original(bytes(data))
        j._hello=corrupt
        value=j.wait();assert value['status']=='UNKNOWN_OBSERVER_ERROR',value
        assert not j.receiver.acknowledged and not j.guard.exists()

def hello_identity_and_deferred_root_hash_models():
    assert template is not None
    for at in (0,8,12,16,20,24,32,40,56,88,120,128):
        data=bytearray(template);data[at]^=1
        if at!=128:data[128:]=sha256(data[:128]).digest()
        reject(lambda data=data:R.decode_hello(bytes(data),proof,nonce))
    root=R.Identity(0,123456,100,42,R.LIVE_PATH,'') # explicit policy model, no root process
    v=R.capture_helper(root.pid,0,R.LIVE_PATH,'a'*64,lambda pid:root,mode='live')
    assert v.expected_image_sha256=='a'*64 and v.identity.image_sha256==''
    data=bytearray(template);struct.pack_into('<IIQQ',data,16,root.uid,root.pid,root.sec,root.usec);data[88:120]=bytes.fromhex('a'*64);data[128:]=sha256(data[:128]).digest()
    assert R.decode_hello(bytes(data),v,nonce)['kernel_peer_and_self_image_checked']
    data[88]^=1;data[128:]=sha256(data[:128]).digest();reject(lambda:R.decode_hello(bytes(data),v,nonce))

def quoted_shell_paths():
    name="quote ' and $literal "+secrets.token_hex(2)
    with job(name=name) as j:
        value=j.wait();assert value['status']=='HOST_RETURN_OBSERVED',value

def case(name,fn):
    start=time.monotonic()
    try:fn();results.append({'name':name,'status':'PASS','seconds':time.monotonic()-start})
    except BaseException as e:
        results.append({'name':name,'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()})
        S.put(HERE/('supervisor-failure-'+str(time.time_ns())+'.json'),{'results':results});raise

if __name__=='__main__':
    for fn in (full_launch,relay_not_owner,observation_timeout_same_pending_owner,retained_and_cross_instance_fence,
               install_digest_failure_and_forged_relay,wrong_expected_helper_digest,source_hazards,one_attempt_wrapper,
               native_render_only,recorded_file_not_live_authentication,public_report_truncation_while_profile_pending,
               hello_ack_timeout_no_owner,stop_between_hello_and_ack,corrupted_self_image_hello_no_ack,
               hello_identity_and_deferred_root_hash_models,quoted_shell_paths):case(fn.__name__,fn)
    report={'status':'PASS_FIXED_LAUNCH_SUPERVISOR','tests_run':len(results),'results':results,
            'native_helper_executed':False,'root_or_administrator_operations':0,'real_device_operations':0,
            'root_cross_UID_tested':False,'root0500_deferred_digest_is_policy_model_only':True,
            'fake_vendor_START_only_in_marked_nonIOKit_fixture':True,'observation_timeout_does_not_restart':True,
            'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'python_sources':{n:sha256((HERE/n).read_bytes()).hexdigest() for n in ('supervisor.py','controller_ipc.py','fixed_launch.py','receipt_receiver.py')},
            'build_receipt_sha256':sha256((HERE/'build-receipt-v2.json').read_bytes()).hexdigest()}
    S.put(HERE/'supervisor-results.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='results'}))
