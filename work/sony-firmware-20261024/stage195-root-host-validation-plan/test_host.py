"""Host-only executable fixtures. Root artifact is never executed by tests."""
from pathlib import Path
from hashlib import sha256
from contextlib import contextmanager
import json,os,secrets,stat,struct,subprocess,time,traceback
import host_supervisor as S
import host_records as H
import host_plan as P
import receipt_receiver as R
HERE=S.HERE;results=[];template_trial=None;template_query=None;template_context=None

def reject(fn):
    try:fn()
    except (OSError,ValueError):return
    raise AssertionError('invalid host input accepted')

@contextmanager
def session(**kw):
    j=S.Session.fixture_session(**kw)
    try:yield j
    finally:
        if j.runner.poll() is None:
            for stage in j.stages:
                stage.frame.stop() # data-only cooperation, no kill/reset
        j.runner.wait(timeout=8);j.stdout.flush();j.stderr.flush()
        err=(j.directory/'launcher-stderr.txt').read_bytes()
        log=(j.directory/'relay-stdout.txt').read_bytes() if (j.directory/'relay-stdout.txt').exists() else b''
        assert b'ERROR: AddressSanitizer' not in err+log and b'runtime error:' not in err+log,(err,log)
        j.close_observer()

def until_trial(j):
    end=time.monotonic()+4
    while time.monotonic()<end:
        j.runner.poll();j.trial.step()
        if j.trial.record:return
        assert not j.trial.error,j.trial.error
        time.sleep(.003)
    raise AssertionError('actual trial record never arrived')

def full_private_trial_and_readback():
    global template_trial,template_query,template_context
    with session() as j:
        value=j.wait();assert value['status']=='HOST_TRIAL_AND_READBACK_COMPLETE',value
        assert j.trial.record['transport_authenticated'] and j.query.record['transport_authenticated']
        assert j.trial.verified.identity.pid!=j.query.verified.identity.pid
        assert j.trial.frame.nonce!=j.query.frame.nonce
        assert j.query.record['archive_sha256']==j.trial.record['record_sha256']
        archive=j.protected/'host-result.bin';assert archive.read_bytes()==j.trial.raw
        assert stat.S_IMODE(archive.stat().st_mode)==0o600
        assert stat.S_IMODE((j.protected/'helper').stat().st_mode)==0o500
        assert not value['physical_camera_acceptance'] and not value['automatic_retry']
        template_trial=j.trial.raw;template_query=j.query.raw
        template_context=(j.trial.verified.identity,j.query.verified.identity,j.trial.frame.nonce,j.query.frame.nonce)
        (HERE/'sample-host-trial.bin').write_bytes(template_trial);(HERE/'sample-host-query.bin').write_bytes(template_query)
        S.put(HERE/'sample-context.json',{'trial_identity':template_context[0].__dict__,'query_identity':template_context[1].__dict__,
            'trial_nonce':template_context[2].hex(),'query_nonce':template_context[3].hex(),'fixture_only':True})

def query_without_saved_live_trial_proof():
    with session() as j:
        until_trial(j)
        expected=j.trial.record['record_sha256'];j.trial.record=None;j.trial.verified=None
        j.trial.step=lambda seconds=.02:None # explicit loss of first-stage live context; same observer PID
        (j.directory/'trial-live-record.json').write_text('{"transport_authenticated":true,"forged":true}')
        value=j.wait();assert value['status']=='HOST_TRIAL_AND_READBACK_COMPLETE',value
        assert j.query.record['archive_sha256']==expected and j.query.record['transport_authenticated']
        assert not j.query.record['archive']['transport_authenticated'] # original context is not resurrected

def saved_file_parse_is_not_transport_authentication():
    value=H.trial(template_trial)
    assert not value['transport_authenticated'] and not value['physical_camera_acceptance']
    t,q,a,b=template_context
    value=H.readback(template_query,q,b,a)
    assert not value['transport_authenticated']

def rejected_archive(kind):
    with session() as j:
        until_trial(j);p=j.protected/'host-result.bin'
        if kind=='mode':os.chmod(p,0o644)
        elif kind=='partial':p.write_bytes(p.read_bytes()[:255])
        elif kind=='checksum':
            data=bytearray(p.read_bytes());data[96]^=1;p.write_bytes(data)
        elif kind=='symlink':
            original=p.with_name('original-host-result.bin');p.rename(original);p.symlink_to(original)
        elif kind=='hardlink':os.link(p,p.with_name('second-host-result.bin'))
        elif kind=='missing':p.rename(p.with_name('retained-original.bin'))
        else:raise AssertionError('unknown fixture')
        value=j.wait();assert value['status']=='UNKNOWN_HOST_TEST',value
        assert j.query.record is None and (j.protected/'readback.once').exists()

def wrong_installed_hash():
    with session(bad_digest=True) as j:
        value=j.wait();assert value['status']=='UNKNOWN_ENTRY_NOT_VERIFIED',value
        assert j.trial.verified is None and not (j.protected/'trial.once').exists()
        assert j.runner.poll()==78

def replay_wrapper_and_entry_denied():
    with session() as j:
        assert j.wait()['status']=='HOST_TRIAL_AND_READBACK_COMPLETE';j.runner.wait(timeout=2)
        before=(j.protected/'host-result.bin').read_bytes()
        r=subprocess.run(['/bin/sh',str(j.command)],capture_output=True,timeout=2);assert r.returncode
        argv=[j.expected_path,'trial',str(j.trial.frame.path),j.trial.frame.nonce.hex(),str(j.sockpaths[0]),str(j.protected)]
        r=subprocess.run(argv,capture_output=True,timeout=3);assert r.returncode==67 and b'single_attempt_consumed' in r.stderr
        assert (j.protected/'host-result.bin').read_bytes()==before
        (j.directory/'entry-replay-stderr.txt').write_bytes(r.stderr)

def refusal_before_work_on_stop():
    with session() as j:
        # Cancel the user frame before any parent entry ACK or private archive.
        j.trial.frame.stop();value=j.wait()
        assert value['status'] in ('UNKNOWN_ENTRY_NOT_VERIFIED','UNKNOWN_HOST_TEST'),value
        assert not (j.protected/'host-result.bin').exists() and not (j.protected/'readback.once').exists()

def host_record_bounds_and_nonce_replay():
    t,q,a,b=template_context
    for at in (0,8,12,16,20,24,28,32,40,48,64,96,128,160,164,176,180,224):
        data=bytearray(template_trial);data[at]^=1
        if at!=224:data[224:]=sha256(data[:224]).digest()
        reject(lambda data=data:H.trial(bytes(data),identity=t,nonce=a))
    for cut in (0,64,255,257):reject(lambda cut=cut:H.trial(template_trial[:cut] if cut<256 else template_trial+b'X'))
    reject(lambda:H.readback(template_query,q,b,b)) # fresh and archived nonce are not interchangeable
    reject(lambda:H.readback(template_query,q,a,a))
    reject(lambda:H.trial(template_trial,identity=q,nonce=a))
    value=H.trial(template_trial,identity=t,nonce=a);assert value['scope']=='HOST_ONLY'

def nonce_bound_query_and_scope():
    t,q,a,b=template_context
    for at in (0,8,12,16,20,24,28,32,40,48,64,96,352):
        data=bytearray(template_query);data[at]^=1
        if at!=352:data[352:]=sha256(data[:352]).digest()
        reject(lambda data=data:H.readback(bytes(data),q,b,a))

def quoted_paths_remain_data():
    with session(name="quote ' $literal "+secrets.token_hex(3)) as j:
        value=j.wait();assert value['status']=='HOST_TRIAL_AND_READBACK_COMPLETE',value

def case(name,fn):
    start=time.monotonic()
    try:fn();results.append({'name':name,'status':'PASS','seconds':time.monotonic()-start})
    except BaseException as e:
        results.append({'name':name,'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()})
        S.put(HERE/('host-failure-'+str(time.time_ns())+'.json'),{'results':results});raise

if __name__=='__main__':
    case('full_private_trial_and_readback',full_private_trial_and_readback)
    case('fresh_query_without_saved_trial_live_proof',query_without_saved_live_trial_proof)
    case('saved_file_parse_is_not_authenticated',saved_file_parse_is_not_transport_authentication)
    for kind in ('mode','partial','checksum','symlink','hardlink','missing'):case('archive_'+kind+'_rejected',lambda kind=kind:rejected_archive(kind))
    for fn in (wrong_installed_hash,replay_wrapper_and_entry_denied,refusal_before_work_on_stop,host_record_bounds_and_nonce_replay,nonce_bound_query_and_scope,quoted_paths_remain_data):case(fn.__name__,fn)
    report={'status':'PASS_HOST_ONLY_TRIAL_AND_READBACK','tests_run':len(results),'results':results,
            'root_candidate_executed':False,'administrator_or_camera_operations':0,'unprivileged_kernel_peer_handshakes':True,
            'root_protected_path_or_cross_UID_validated':False,'cleared_live_context_in_same_observer_process_explicit':True,
            'real_Orca_restart_and_power_loss_not_tested':True,'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'build_receipt_sha256':sha256((HERE/'build-receipt.json').read_bytes()).hexdigest(),
            'python_sources':{n:sha256((HERE/n).read_bytes()).hexdigest() for n in ('host_supervisor.py','host_records.py','host_plan.py','controller_ipc.py','receipt_receiver.py')}}
    S.put(HERE/'host-test-results.json',report);print(json.dumps({k:v for k,v in report.items() if k!='results'}))
