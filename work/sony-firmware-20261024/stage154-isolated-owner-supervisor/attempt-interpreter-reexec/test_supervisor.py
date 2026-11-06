#!/usr/bin/env python3
"""Real child processes, own C fixtures only; no IOKit candidate is loaded."""
from pathlib import Path
import json
import signal
import time
import owner_binding as B
import owner_supervisor as S
from shared_job import put_once

HERE=Path(__file__).resolve().parent


def wait_for(check,seconds=2):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=check()
        if value:return value
        time.sleep(0.01)
    raise AssertionError('bounded test observation expired')


def wait_state(job,predicate,seconds=2):
    def check():
        state=job.poll()
        return state if predicate(state) else None
    return wait_for(check,seconds)


def terminal(job):
    return wait_state(job,lambda state:state.get('worker_terminal_verified'),4)


def main():
    out=HERE/'run-process-tests';out.mkdir(exist_ok=False)
    cases=[];jobs=[]
    def start(name,options=None,**kwargs):
        job=S.Job.start_fixture(out/name,options,**kwargs);jobs.append(job);return job
    def done(job,name):
        state=terminal(job);cases.append({'name':name,'state':state});return state
    try:
        job=start('normal')
        state=done(job,'normal_receipt_and_process_exit')
        assert state['status']=='PROVIDER_OBSERVATION_COMPLETED' and state['native_function_return_verified']
        assert state['calls']['4']==state['calls']['10']==1 and not state['physical_acceptance']
        try:S.Job.start_fixture(job.directory)
        except B.Rejected:cases.append({'name':'same_job_single_use','rejected_before_second_spawn':True})
        else:raise AssertionError('same consumed job was restarted')

        job=start('cooperative-stop',{'block_phase':4},work_s=1,total_s=3)
        blocked=wait_state(job,lambda state:state.get('fixture_gate_entered')==4)
        assert blocked['verified_worker_alive'] and blocked['active_native_call_phase']==4
        recovered=S.observe_recorded(job.directory)
        assert recovered['verified_worker_alive'] and not recovered['restarted']
        job.request_stop();time.sleep(0.03)
        held=job.poll();assert held['verified_worker_alive'] and held['stop_requested'] and held['active_native_call_phase']==4
        try:job.close_terminal()
        except B.Rejected:pass
        else:raise AssertionError('observer mapping closed while native worker was alive')
        job.shared.release_fixture()
        state=done(job,'stop_during_block_only_cleans_after_native_return')
        assert state['status']=='PROVIDER_ABORTED_OBSERVATION' and state['calls']['5']==state['calls']['7']==0
        assert state['calls']['10']==state['calls']['11']==1
        cases.append({'name':'resume_observer_verified_live_incarnation','state':recovered,'blocked_state':held})

        job=start('overdue-call',{'block_phase':4},work_s=2,total_s=3)
        wait_for(lambda:job.poll().get('fixture_gate_entered')==4)
        time.sleep(max(0,(job.spec['final_deadline_ns']-time.monotonic_ns())/1e9)+0.05)
        overdue=job.poll();assert overdue['verified_worker_alive'] and overdue['final_deadline_passed'] and overdue['stop_requested']
        assert overdue['active_native_call_phase']==4 and not overdue['restarted_or_killed']
        job.shared.release_fixture()
        state=done(job,'deadline_does_not_kill_or_retry_pending_native_call')
        assert state['status']=='UNKNOWN_PROVIDER_STATE' and state['calls']['10']==state['calls']['11']==1
        cases.append({'name':'actual_handle_verified_alive_after_deadline','state':overdue})

        job=start('signal-stop',{'block_phase':4},work_s=1,total_s=3)
        wait_for(lambda:job.poll().get('fixture_gate_entered')==4)
        job.process.send_signal(signal.SIGTERM)  # Own marked fixture only.
        stopped=wait_state(job,lambda state:state.get('stop_requested'))
        assert stopped['verified_worker_alive'] and stopped['active_native_call_phase']==4
        job.shared.release_fixture();state=done(job,'SIGTERM_is_cooperative_stop_not_forced_exit')
        assert state['status']=='PROVIDER_ABORTED_OBSERVATION' and state['returncode']==0

        job=start('result-before-exit',{'receipt_delay_s':0.5})
        wait_for(lambda:(job.directory/'native-returned.json').exists())
        early=job.poll();assert early['verified_worker_alive'] and early['active_native_call_phase']==0
        assert early['status']=='WORKER_RUNNING'
        state=done(job,'native_return_record_does_not_imply_worker_exit')
        assert state['status']=='PROVIDER_OBSERVATION_COMPLETED'

        for name,options in [('missing-receipt',{'exit_without_receipt':True}),('wrong-receipt',{'bad_receipt_nonce':True})]:
            job=start(name,options);state=done(job,name)
            assert state['status'].startswith('UNKNOWN_TERMINAL') and not state['physical_acceptance']

        job=start('observer-error',{'block_phase':4},work_s=1,total_s=3)
        wait_for(lambda:job.poll().get('fixture_gate_entered')==4)
        original=job.process.poll
        def observation_error():raise OSError('fixture transient observation failure')
        job.process.poll=observation_error
        try:
            transient=job.poll();assert transient['status']=='OBSERVATION_ERROR_UNRESOLVED'
        finally:job.process.poll=original
        assert job.poll()['verified_worker_alive']
        original_identity=S.process_identity
        S.process_identity=lambda pid:observation_error()
        try:
            missing=S.observe_recorded(job.directory);assert missing['status']=='OBSERVATION_ERROR_UNRESOLVED'
        finally:S.process_identity=original_identity
        assert S.observe_recorded(job.directory)['verified_worker_alive']
        job.request_stop();job.shared.release_fixture();done(job,'transient_observation_error_does_not_restart_worker')

        job=start('dead-fixture',{'block_phase':4},work_s=1,total_s=3)
        wait_for(lambda:job.poll().get('fixture_gate_entered')==4)
        assert job.spec['mode']=='fixture'
        job.process.kill()  # Intentional failure injection into own non-IOKit fixture, never the supervisor policy.
        state=done(job,'own_fixture_death_keeps_native_state_unknown')
        assert state['status']=='UNKNOWN_TERMINAL_WITHOUT_VALID_RECEIPT' and state['returncode']<0
        assert job.shared.progress()['active_native_call_phase']==4
        missing=S.observe_recorded(job.directory);assert not missing['verified_worker_alive'] and not missing['restarted']

        for label in ['no_arguments','future_flags_do_not_create_live_worker']:
            try:S.Job.start_live(out/'must-not-exist')
            except B.Rejected:cases.append({'name':label,'rejected_before_process_or_native_load':True})
            else:raise AssertionError('live start unexpectedly allowed')
            assert not (out/'must-not-exist').exists()
    finally:
        # Always release our deliberately blocked providers. Do not kill a child
        # as cleanup and do not reinterpret missing native results as restoration.
        for job in jobs:
            if job.process.poll() is None:
                job.request_stop();job.shared.release_fixture()
                wait_for(lambda:job.process.poll() is not None,4)
            job.close_terminal()
    result={'status':'PASS_REAL_CHILD_FIXTURE_SUPERVISION_NOT_IOKIT_OR_CAMERA_ACCEPTANCE','checks':len(cases),'cases':cases,
        'fixture_worker_jobs':len(jobs),'all_created_fixture_workers_terminal':all(j.process.poll() is not None for j in jobs),
        'real_IOKit_candidate_loaded_or_device_operations':False,
        'intentional_signal_and_kill_injection_scoped_to_own_fixtures_only':True,
        'actual_driver_return_or_HEVC_recording_proven':False}
    put_once(out/'results.json',result)
    (out/'test-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'checks':len(cases),'fixture_jobs':len(jobs),'all_fixture_children_terminal':True}))


if __name__=='__main__':main()
