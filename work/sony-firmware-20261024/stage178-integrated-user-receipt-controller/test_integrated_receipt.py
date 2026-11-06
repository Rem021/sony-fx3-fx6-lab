"""User-only real wrapper/fixture integration. No sudo, app or USB execution."""
from pathlib import Path
from hashlib import sha256
import json
import os
import stat
import subprocess
import time
import launch_policy as P
import owner_supervisor as S

HERE=Path(__file__).resolve().parent

def until(job,predicate,seconds=5):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=job.poll()
        if predicate(value):return value
        time.sleep(.01)
    raise AssertionError(('own user fixture timed out',value))

def main():
    root=HERE/'runs/integrated-receipt-tests';root.mkdir(mode=0o700,exist_ok=False)
    cases=[];jobs=[]
    def start(name,**args):
        job=S.Job.start_terminal_fixture(root/name,**args);jobs.append(job);return job
    try:
        job=start('normal',block_phase=4)
        value=until(job,lambda s:s.get('active_native_call_phase')==4)
        assert job.relay.poll()==0 and value['verified_helper_alive'] and job.ack_sent
        assert job.fixture_terminal_runner.poll() is None
        cases.append({'name':'actual_wrapper_keeps_command_runner_separate_from_completed_open_request'})
        job.frame.release_fixture()
        value=until(job,lambda s:s.get('helper_terminal_verified'))
        job.fixture_terminal_runner.wait(timeout=3)
        assert value['status']=='PROVIDER_OBSERVATION_COMPLETED'
        assert value['receipt']['result_sha256']==bytes(job.frame.grant.result_sha256).hex()
        result=P.read_helper_receipt(job.directory);st=job.out_path.stat()
        assert st.st_uid==501 and stat.S_IMODE(st.st_mode)==0o600
        assert result['pid']==job.identity['pid'] and P.terminal_returncode(job.directory,job.frame.nonce.hex())==0
        cases.append({'name':'same_production_wrapper_user_stdout_consumed_by_full_identity_ACK_SHA_supervisor','result':value})

        digest=sha256(job.out_path.read_bytes()).hexdigest()
        rerun=subprocess.run(['/bin/sh',str(job.directory/'fixture-command.sh')],capture_output=True,text=True)
        assert rerun.returncode!=0 and sha256(job.out_path.read_bytes()).hexdigest()==digest
        cases.append({'name':'actual_wrapper_replay_preserves_result_and_does_not_reenter_helper'})

        job=start('bad-hash',bad_digest=True)
        value=until(job,lambda s:s['status'].startswith('UNKNOWN_TERMINAL'))
        job.fixture_terminal_runner.wait(timeout=3)
        assert value['relay_returncode']==78 and not job.frame.ready() and not job.ack_sent
        assert job.out_path.stat().st_uid==501 and stat.S_IMODE(job.out_path.stat().st_mode)==0o600
        cases.append({'name':'bad_installed_hash_preserves_readable_user_output_and_command_exit78'})

        job=start('missing-result',block_phase=4);until(job,lambda s:s.get('active_native_call_phase')==4)
        job.frame.release_fixture();job.fixture_terminal_runner.wait(timeout=3)
        job.out_path.rename(job.directory/'retained-original-result.txt')
        value=until(job,lambda s:s.get('helper_terminal_verified'))
        assert value['status']=='UNKNOWN_TERMINAL_RECEIPT_MISMATCH' and value['receipt_error']['errno']==2
        assert (job.directory/'retained-original-result.txt').exists()
        cases.append({'name':'missing_result_retains_UNKNOWN_and_specific_errno_without_restart','state':value})

        # Existing consumed05 root-owned file: metadata rejection only. The
        # new reader neither opens its contents nor changes access permissions.
        old=Path('/private/tmp/fx3-702-msc-owner-20261029-05')
        st=(old/'relay-stdout.txt').lstat();assert st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o600
        try:P.read_helper_receipt(old)
        except P.ReceiptRejected as error:
            assert error.category=='helper_receipt_file_identity_or_size' and error.metadata['uid']==0
            cases.append({'name':'actual05_root0600_receipt_rejected_with_owner_reason_before_contents','reason':P.receipt_error_info(error)})
        else:raise AssertionError('root-owned output unexpectedly accepted')

        malformed=[('empty',b'',0o600),('wide-mode',b'{}',0o644),('oversize',b'x'*16385,0o600),
                   ('invalid-json',b'{',0o600),('nonobject',b'[]',0o600)]
        for name,data,mode in malformed:
            d=root/name;d.mkdir(mode=0o700)
            fd=os.open(d/'relay-stdout.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
            with os.fdopen(fd,'wb') as f:f.write(data)
            try:P.read_helper_receipt(d)
            except P.ReceiptRejected as error:cases.append({'name':'private_reader_rejects_'+name,'reason':P.receipt_error_info(error)})
            else:raise AssertionError('malformed result accepted')
        d=root/'symlink';d.mkdir(mode=0o700);(d/'relay-stdout.txt').symlink_to(root/'wide-mode/relay-stdout.txt')
        try:P.read_helper_receipt(d)
        except P.ReceiptRejected:cases.append({'name':'result_symlink_not_followed'})
        else:raise AssertionError('result symlink accepted')

        command,body=P.native_terminal('01'*16)
        assert body.splitlines()[-1].endswith(' 2>&1') and 'relay-stdout.txt' not in body and 'relay-stderr.txt' not in body
        assert 'relay-stdout.txt; then' in command and '/usr/bin/sudo -- ' in command
        assert 'sudo -S' not in command and 'sudo -A' not in command
        assert not P.JOB_DIR.exists() and not (HERE/'physical-grant-attempt.claim').exists()
        cases.append({'name':'production_source_uses_user_stdout_only_no_new_native_grant_consumed'})
    finally:
        for job in jobs:
            if job.fixture_terminal_runner.poll() is None:
                job.request_stop();job.frame.release_fixture();job.fixture_terminal_runner.wait(timeout=3)
            job.relay.wait(timeout=3)
            if not job.frame.terminal:job.frame.terminal=True # own non-IOKit fixture only
            job.close_terminal()
    report={'status':'PASS_INTEGRATED_USER_RECEIPT_WRAPPER_AND_SUPERVISOR','checks':len(cases),'cases':cases,
        'new_root_sudo_Terminal_or_native_IOKit_execution':False,'camera_operations':0,
        'actual_root_owned05_file_metadata_checked':True,'actual_root_owned05_contents_read_or_permissions_changed':False}
    with (HERE/'integrated-receipt-tests.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'integrated_receipt_checks':len(cases),'new_root_or_camera_operations':0}))

if __name__=='__main__':main()
