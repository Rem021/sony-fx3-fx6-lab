#!/usr/bin/env python3
"""Exercise the fixed C fixture executable and shell staging without root/USB."""
from pathlib import Path
from hashlib import sha256
import json
import os
import subprocess
import time
import entry_binding as E
import owner_supervisor as S
import launch_policy as P

HERE=Path(__file__).resolve().parent


def wait(job,predicate,*,seconds=5,ack=True):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        state=job.poll(allow_ack=ack)
        if predicate(state):return state
        time.sleep(.01)
    raise AssertionError(('fixture observation timeout',state))


def main():
    root=HERE/'runs/hardened-entry-tests';root.mkdir(mode=0o700,exist_ok=False)
    cases=[];jobs=[];direct=[]
    build=P.checked_build();assert 'IOKit' not in build['fixture']['dependencies']
    def start(name,**kwargs):
        j=S.Job.start_fixture(root/name,**kwargs);jobs.append(j);return j
    def finish(j,ack=True):return wait(j,lambda s:s.get('helper_terminal_verified') or s['status'].startswith('UNKNOWN_TERMINAL'),ack=ack)
    try:
        j=start('normal');r=finish(j)
        assert r['status']=='PROVIDER_OBSERVATION_COMPLETED' and j.ack_sent
        assert r['receipt']['fixture_calls']==[1,1,1,1,1,1,1,0,1,1,1,1]
        assert r['helper_identity']['path']==str(j.directory/'staged-grant/helper')
        cases.append({'name':'actual_staging_hash_kernel_identity_ACK_and_terminal_receipt','result':r})
        original_lease=sha256((j.directory/'staged-grant/entry.once').read_bytes()).hexdigest()
        replay=start('new-frame-same-grant',stage_dir=j.directory/'staged-grant');rr=finish(replay)
        assert rr['status'].startswith('UNKNOWN_TERMINAL') and replay.frame.grant.native_started==0
        assert sha256((j.directory/'staged-grant/entry.once').read_bytes()).hexdigest()==original_lease
        cases.append({'name':'new_frame_cannot_reuse_staging_grant','relay_returncode':rr['relay_returncode']})

        # Even bypassing the staging mkdir cannot reuse the C entry's fixed lease.
        d=root/'direct-replay';d.mkdir(mode=0o700);f=E.Frame(d/'shared.bin',E.IPC())
        p=subprocess.Popen([str(j.directory/'staged-grant/helper'),str(f.path),f.nonce.hex(),str(j.directory/'staged-grant/entry.once')],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        direct.append((p,f));out,err=p.communicate(timeout=3)
        assert p.returncode==67 and b'fixed_grant_consumed' in err and f.grant.attempt_claimed==0
        cases.append({'name':'direct_C_replay_with_new_frame_denied_before_provider','exit':p.returncode})

        j=start('bad-copied-hash',bad_digest=True);r=finish(j)
        assert r['relay_returncode']==78 and not j.frame.ready() and j.frame.grant.native_started==0
        cases.append({'name':'copied_executable_digest_mismatch_never_executed','exit':78})

        j=start('no-ACK');r=finish(j,ack=False)
        assert r['status']=='PROVIDER_DENIED' and not j.ack_sent and j.frame.grant.native_started==0
        assert sum(r['receipt']['fixture_calls'])==0
        cases.append({'name':'unacknowledged_helper_times_out_without_any_provider','result':r})

        j=start('wrong-controller-path',expected_path='/different/reviewed/helper');r=finish(j)
        assert r['status'].startswith('UNKNOWN_TERMINAL') and not j.ack_sent and j.frame.grant.native_started==0
        cases.append({'name':'wrong_helper_path_withholds_ACK_and_requests_stop','native_started':False})

        j=start('wrong-body',expected_tag=bytes([0x42])*32);r=finish(j)
        assert r['status']=='UNKNOWN_PROVIDER_STATE' and r['receipt']['fixture_calls'][0]==1
        assert sum(r['receipt']['fixture_calls'])==1
        cases.append({'name':'wrong_body_denied_after_ACK_before_userclient','result':r})

        j=start('pending-past-deadline',block_phase=4)
        r=wait(j,lambda s:s.get('active_native_call_phase')==4)
        pid=j.identity['pid'];time.sleep(1.6);r=j.poll()
        assert r['verified_helper_alive'] and r['final_deadline_passed'] and r['active_native_call_phase']==4
        assert j.frame.grant.native_pid==pid and j.relay.poll() is None
        assert E.B.Control.from_buffer_copy(j.frame.mapping[:16]).stop_requested==1
        cases.append({'name':'watchdog_deadline_sets_stop_pending_helper_stays_alive','state':r,'pid':pid})
        j.frame.release_fixture();r=finish(j)
        assert r['status']=='UNKNOWN_PROVIDER_STATE' and r['receipt']['fixture_calls'][4]==r['receipt']['fixture_calls'][6]==0
        assert r['receipt']['fixture_calls'][9]==r['receipt']['fixture_calls'][10]==1
        cases.append({'name':'pending_call_returns_then_single_cleanup_without_retry','result':r})

        j=start('metadata-transient',block_phase=4);wait(j,lambda s:s.get('active_native_call_phase')==4)
        original=j.frame.ipc.identity
        def transient(pid):raise OSError('injected metadata lookup failure')
        j.frame.ipc.identity=transient;r=j.poll()
        assert r['status']=='HELPER_OBSERVATION_ERROR_UNRESOLVED' and j.relay.poll() is None
        j.poll();logs=list(j.directory.glob('observation-error-*.json'))
        assert len(logs)==1 and json.loads(logs[0].read_text())['phase']=='helper_identity'
        original_put=S.put
        def log_failed(path,value):
            if path.name.startswith('observation-error-'):raise OSError('injected diagnostic storage failure')
            return original_put(path,value)
        def another_transient(pid):raise OSError('second injected identity observation failure')
        S.put=log_failed;j.frame.ipc.identity=another_transient
        try:
            log_state=j.poll()
            assert log_state['status']=='HELPER_OBSERVATION_ERROR_UNRESOLVED'
            assert 'injected diagnostic storage failure' in log_state['observation_log_error']
            assert j.relay.poll() is None
            cases.append({'name':'diagnostic_storage_failure_keeps_pending_worker_observed','state':log_state})
        finally:S.put=original_put
        j.frame.ipc.identity=original;r=j.poll();assert r['verified_helper_alive']
        j.frame.release_fixture();r=finish(j)
        cases.append({'name':'transient_metadata_failure_not_exit_or_restart','terminal':r['status']})

        j=start('wrong-receipt',block_phase=4);wait(j,lambda s:s.get('active_native_call_phase')==4)
        j.frame.release_fixture()
        end=time.monotonic()+3
        while j.relay.poll() is None and time.monotonic()<end:time.sleep(.01)
        assert j.relay.poll()==0
        corrupt=json.loads(j.out_path.read_text());corrupt['nonce']='00'*16
        j.out_path.write_text(json.dumps(corrupt))
        r=j.poll();assert r['status']=='UNKNOWN_TERMINAL_RECEIPT_MISMATCH' and r['helper_terminal_verified']
        cases.append({'name':'exit_zero_wrong_receipt_keeps_provider_state_unknown','state':r})

        goal=json.loads((HERE.parent/'GOAL_STATUS.json').read_text())
        try:P.live_authority(goal)
        except E.B.Rejected as error:cases.append({'name':'current_live_authority_denied_before_prompt_frame_or_cache','reason':str(error)})
        else:raise AssertionError('current authority unexpectedly allows live')
        assert not (HERE/'physical-grant-attempt.claim').exists()
        assert not P.JOB_DIR.exists()
    finally:
        for j in jobs:
            if j.relay.poll() is None:
                j.request_stop();j.frame.release_fixture()
                wait(j,lambda s:s.get('helper_terminal_verified') or s['status'].startswith('UNKNOWN_TERMINAL'),ack=False)
            if j.relay.poll() is not None and not j.frame.terminal:j.frame.terminal=True # own non-IOKit fixture only
            j.close_terminal()
        for p,f in direct:
            if p.poll() is None:f.stop();f.release_fixture();p.communicate(timeout=3)
            f.terminal=True;f.close_terminal()
    report={'status':'PASS_HARDENED_FIXTURE_LAUNCH_NOT_ROOT_OR_USB_ACCEPTANCE','checks':len(cases),'cases':cases,
        'fixture_jobs':len(jobs),'additional_fixture_processes':len(direct),'all_fixture_relays_terminal':all(j.relay.poll() is not None for j in jobs),
        'root_or_native_IOKit_helper_or_administrator_prompt_executed':False,'new_camera_operations':0}
    with (HERE/'hardened-entry-tests.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'entry-test-executed.py').write_bytes(Path(__file__).read_bytes())
    (HERE/'supervisor-tested.py').write_bytes((HERE/'owner_supervisor.py').read_bytes())
    print(json.dumps({'checks':len(cases),'fixture_jobs':len(jobs),'root_or_device_operations':0}))


if __name__=='__main__':main()
