"""Actual user fixture processes; simulated Terminal completion, no app/sudo/USB."""
from pathlib import Path
import json
import os
import subprocess
import time
import entry_binding as E
import launch_policy as P
import owner_supervisor as S

HERE=Path(__file__).resolve().parent

def until(action,seconds=5):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=action()
        if value:return value
        time.sleep(.01)
    raise AssertionError('own fixture observation timed out')

def marker(job,code=0,**overrides):
    value={'schema':1,'grant_id':P.GRANT_ID,'nonce':job.frame.nonce.hex(),'returncode':code}
    value.update(overrides);S.put(job.directory/'terminal-command-result.json',value)

def main():
    root=HERE/'runs/terminal-relay-tests';root.mkdir(mode=0o700,exist_ok=False)
    cases=[];jobs=[];workers={}
    def empty(name):
        directory=root/name;directory.mkdir(mode=0o700)
        frame=E.Frame(directory/'shared.bin',E.IPC())
        job=S.Job._spawn(directory,frame,['/usr/bin/true'],'/fixture/no-helper',mode='fixture',terminal_relay=True)
        job.relay.wait(timeout=3);jobs.append(job);return job
    try:
        j=empty('open-success-no-helper');state=j.poll()
        assert state['status']=='TERMINAL_COMMAND_COMPLETION_PENDING_HELPER_UNCONFIRMED'
        assert state['Terminal_launch_returncode']==0 and not j.frame.terminal and not j.ack_sent
        cases.append({'name':'open_exit0_does_not_end_or_accept_unstarted_command','state':state})
        marker(j);state=j.poll()
        assert state['status']=='UNKNOWN_TERMINAL_WITHOUT_VERIFIED_HELPER_RECEIPT' and not j.frame.grant.native_started
        cases.append({'name':'command_exit0_without_actual_helper_receipt_stays_unknown','state':state})

        j=empty('sudo-cancel-no-helper');marker(j,1);state=j.poll()
        assert state['status']=='UNKNOWN_TERMINAL_WITHOUT_VERIFIED_HELPER_RECEIPT'
        assert not j.frame.grant.native_started and not j.ack_sent
        cases.append({'name':'cancelled_command_does_not_start_or_accept_helper','state':state})

        j=S.Job.start_fixture(root/'live-fixture-command',block_phase=4);jobs.append(j)
        workers[id(j)]=j.relay
        j.relay=subprocess.Popen(['/usr/bin/true'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        j.relay.wait(timeout=3);j.terminal_relay=True
        def entered():
            value=j.poll()
            return value if value.get('active_native_call_phase')==4 else None
        state=until(entered)
        pid=j.identity['pid'];assert state['verified_helper_alive'] and j.ack_sent
        time.sleep(1.6);state=j.poll()
        assert state['verified_helper_alive'] and state['final_deadline_passed'] and state['active_native_call_phase']==4
        assert j.identity['pid']==pid and workers[id(j)].poll() is None
        assert E.B.Control.from_buffer_copy(j.frame.mapping[:16]).stop_requested==1
        cases.append({'name':'open_exit0_preserves_actual_pending_worker_and_cooperative_deadline','state':state})

        marker(j,nonce='00'*16);state=j.poll()
        assert state['status']=='OBSERVATION_ERROR_UNRESOLVED' and workers[id(j)].poll() is None
        assert not j.frame.terminal
        cases.append({'name':'wrong_nonce_completion_is_observation_error_not_cleanup_or_retry','state':state})
        (j.directory/'terminal-command-result.json').rename(j.directory/'invalid-terminal-command-result.json')
        j.frame.release_fixture();workers[id(j)].wait(timeout=3)
        state=j.poll()
        assert state['status']=='TERMINAL_COMMAND_COMPLETION_PENDING_HELPER_UNCONFIRMED' and not j.frame.terminal
        cases.append({'name':'actual_helper_exit_without_command_marker_is_not_terminal_acceptance','state':state})
        marker(j,workers[id(j)].returncode);state=j.poll()
        assert state['helper_terminal_verified'] and state['status']=='UNKNOWN_PROVIDER_STATE'
        assert state['receipt']['fixture_calls'][9:11]==[1,1]
        cases.append({'name':'actual_identity_and_SHA_receipt_plus_command_completion_allow_single_cleanup_result','state':state})

        for name,payload in [('empty',b''),('invalid-json',b'{'),('noninteger',None),('wrong-grant',None)]:
            d=root/('marker-'+name);d.mkdir(mode=0o700)
            path=d/'terminal-command-result.json'
            if payload is not None:
                fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as f:f.write(payload)
            else:
                value={'schema':1,'grant_id':P.GRANT_ID,'nonce':'01'*16,'returncode':False if name=='noninteger' else 0}
                if name=='wrong-grant':value['grant_id']='different-consumed-grant'
                S.put(path,value)
            try:P.terminal_returncode(d,'01'*16)
            except OSError as error:cases.append({'name':'marker_rejected_'+name,'error':str(error)})
            else:raise AssertionError('invalid completion marker accepted')
        d=root/'marker-symlink';d.mkdir(mode=0o700)
        (d/'terminal-command-result.json').symlink_to(root/'marker-invalid-json/terminal-command-result.json')
        try:P.terminal_returncode(d,'01'*16)
        except OSError:cases.append({'name':'completion_symlink_not_followed'})
        else:raise AssertionError('completion symlink accepted')

        valid={'schema':1,'getauid_return':0,'getaudit_return':0,'security_session_return':0,
            'audit_uid':501,'audit_record_uid':501,'audit_session_id':100022,'security_session_id':100022,
            'security_session_attributes':24624,'has_graphic_access':True,'has_tty':True,'is_remote':False}
        assert P.valid_host_login(valid)
        assert not P.valid_host_login({**valid,'audit_uid':0})
        assert not P.valid_host_login({**valid,'has_graphic_access':False})
        assert not P.valid_host_login({**valid,'security_session_id':100023})
        assert not P.valid_host_login(None)
        cases.append({'name':'receipt_requires_current_user_GUI_audit_session_not_uid0_only','checks':5})

        command,body=P.native_terminal('01'*16)
        example=root/'syntax-only.command';example.write_text(command)
        subprocess.run(['/bin/sh','-n',str(example)],check=True,capture_output=True)
        sudo_line=next(l for l in command.splitlines() if l.startswith('if /usr/bin/sudo'))
        assert ' > ' not in sudo_line and ' 2>' not in sudo_line
        assert body.splitlines()[-1].startswith('exec ') and ' 2> ' in body.splitlines()[-1]
        assert '/Volumes/' not in command and 'terminal-command.once' in command
        assert 'terminal-command-result.json' in command and 'osascript' not in command
        cases.append({'name':'sudo_verification_stays_in_Terminal_only_helper_output_redirected','command_executed':False})

        goal=json.loads((HERE.parent/'GOAL_STATUS.json').read_text())
        try:P.live_authority(goal)
        except E.B.Rejected as error:cases.append({'name':'historical_camera_and_host_grants_cannot_launch05','error':str(error)})
        else:raise AssertionError('new camera grant unexpectedly authorized')
        assert not P.JOB_DIR.exists() and not (HERE/'physical-grant-attempt.claim').exists()
    finally:
        for job in jobs:
            worker=workers.get(id(job))
            if worker is not None:
                job.request_stop();job.frame.release_fixture();worker.wait(timeout=3)
            job.relay.wait(timeout=3)
            if not job.frame.terminal:job.frame.terminal=True # own non-IOKit fixture only
            job.close_terminal()
    report={'status':'PASS_TERMINAL_LAUNCH_AND_COMPLETION_SEPARATED_NO_REAL_TERMINAL_OR_ROOT',
        'checks':len(cases),'cases':cases,'actual_user_fixture_processes':1,
        'Terminal_or_sudo_or_root_or_native_IOKit_executed':False,'camera_operations':0}
    with (HERE/'terminal-relay-tests.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'terminal_relay_checks':len(cases),'real_root_or_Terminal_or_camera_operations':0}))

if __name__=='__main__':main()
