#!/usr/bin/env python3
"""Use actual own-fixture PIDs and parent exit; never root/native IOKit."""
from pathlib import Path
import json
import subprocess
import sys
import time
import entry_binding as E
import owner_supervisor as S

HERE=Path(__file__).resolve().parent


def until(check,seconds=5):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        result=check()
        if result:return result
        time.sleep(.01)
    raise AssertionError('own fixture did not reach observed state')


def main():
    root=HERE/'runs/recorded-observer-tests';root.mkdir(mode=0o700,exist_ok=False)
    cases=[];job=None;attached=None;parent=None
    try:
        job=S.Job.start_fixture(root/'same-live-process',block_phase=4)
        until(lambda:(s:=job.poll()).get('active_native_call_phase')==4)
        state=S.observe_recorded(job.directory)
        assert state['status']=='RECORDED_HELPER_LIVE' and state['verified_helper_alive'] and state['active_native_call_phase']==4
        assert not state['restarted'] and job.relay.poll() is None
        cases.append({'name':'recorded_file_checked_against_current_kernel_identity','state':state})
        original=json.loads((job.directory/'verified-helper.json').read_text())
        wrong=json.loads(json.dumps(original));wrong['identity']['birth_usec']+=1
        (job.directory/'verified-helper.json').write_text(json.dumps(wrong))
        state=S.observe_recorded(job.directory)
        assert state['status']=='UNKNOWN_PID_IDENTITY_DIFFERS' and not state['verified_helper_alive']
        (job.directory/'verified-helper.json').write_text(json.dumps(original))
        cases.append({'name':'recorded_birth_mismatch_not_accepted_as_live','state':state})
        job.frame.release_fixture()
        until(lambda:(s:=job.poll()).get('helper_terminal_verified'))
        state=S.observe_recorded(job.directory)
        assert state['status']=='RECORDED_HELPER_TERMINAL_RESULT_CONSISTENT' and not state['verified_helper_alive']
        cases.append({'name':'actual_kernel_absence_and_consistent_receipt_reported_separately','state':state})

        orphan=root/'departed-parent'
        with (root/'parent-stdout.txt').open('xb') as out,(root/'parent-stderr.txt').open('xb') as err:
            parent=subprocess.Popen([sys.executable,'-B',str(HERE/'fixture_orphan_parent.py'),str(orphan)],
                stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        until(lambda:parent.poll() is not None)
        assert parent.returncode==0 and (orphan/'parent-departure.json').exists()
        attached=E.Frame.attach(orphan/'shared.bin',E.IPC())
        until(lambda:E.B.Control.from_buffer_copy(attached.mapping[:16]).stop_requested==1)
        state=S.observe_recorded(orphan)
        assert state['status']=='RECORDED_HELPER_LIVE' and attached.pending()==4
        cases.append({'name':'actual_parent_exit_watchdog_requests_stop_without_killing_pending_helper','state':state})
        attached.release_fixture()
        state=until(lambda:(s:=S.observe_recorded(orphan)) if s.get('helper_terminal_verified') and s['status'].endswith('CONSISTENT') else None)
        assert state['native']['status_code'] in (1,2)
        receipt=json.loads((orphan/'relay-stdout.txt').read_text());calls=receipt['fixture_calls']
        assert calls[4]==calls[6]==0 and calls[9]==calls[10]==1
        cases.append({'name':'orphaned_fixture_returns_and_cleans_once_no_restart','state':state})
    finally:
        if job is not None:
            if job.relay.poll() is None:
                job.request_stop();job.frame.release_fixture();until(lambda:job.poll().get('helper_terminal_verified'))
            job.frame.terminal=True;job.close_terminal()
        if attached is not None:
            attached.stop();attached.release_fixture()
            until(lambda:S.observe_recorded(root/'departed-parent').get('helper_terminal_verified'))
            attached.terminal=True;attached.close_terminal()
    report={'status':'PASS_RECORDED_OBSERVER_AND_ACTUAL_OWN_PARENT_EXIT_NOT_ROOT_OR_CAMERA_ACCEPTANCE','checks':len(cases),'cases':cases,
        'fixture_helpers':2,'orphan_parent_processes':1,'native_IOKit_or_admin_executed':False,'new_device_operations':0}
    with (HERE/'recorded-observer-tests.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    (HERE/'observer-test-executed.py').write_bytes(Path(__file__).read_bytes())
    (HERE/'observer-supervisor-tested.py').write_bytes((HERE/'owner_supervisor.py').read_bytes())
    print(json.dumps({'recorded_observer_checks':len(cases),'actual_own_parent_exit_exercised':True,'root_or_device_operations':0}))


if __name__=='__main__':main()
