#!/usr/bin/env python3
"""Real user-only copies and a non-IOKit fixture, never admin/native USB."""
from pathlib import Path
from hashlib import sha256
import json
import os
import stat
import subprocess
import tempfile
import time
import entry_binding as E
import launch_policy as P
import owner_supervisor as S

HERE=Path(__file__).resolve().parent


def wait(job,predicate):
    end=time.monotonic()+5
    while time.monotonic()<end:
        value=job.poll()
        if predicate(value):return value
        time.sleep(.01)
    raise AssertionError(('fixture timed out',value))


def main():
    work=HERE/'runs/internal-stage-tests';work.mkdir(mode=0o700)
    temporary=Path(tempfile.mkdtemp(prefix='fx3-owner-stage178-fixture-',dir='/private/tmp'))
    build=P.checked_build();fixture=HERE/build['fixture']['path'];digest=build['fixture']['sha256']
    assert 'IOKit' not in build['fixture']['dependencies']
    source=work/'fixture-source';source.write_bytes(fixture.read_bytes())
    cases=[];job=None
    def directory(name):
        p=temporary/name;p.mkdir(mode=0o700);return p
    def denied(name,action,path):
        try:action()
        except (E.B.Rejected,OSError) as error:
            cases.append({'name':name,'rejected':type(error).__name__,'destination_not_created':not path.exists()})
        else:raise AssertionError('expected rejection: '+name)
    try:
        good=directory('good');receipt=P.stage_source(source,digest,good)
        assert sha256((good/'source-helper').read_bytes()).hexdigest()==digest
        assert stat.S_IMODE((good/'source-helper').stat().st_mode)==0o500
        assert stat.S_IMODE(good.stat().st_mode)==0o700
        cases.append({'name':'actual_internal_exclusive_copy_hash_and_permissions','receipt':receipt})

        bad=directory('bad-digest')
        denied('wrong_digest_no_private_executable',lambda:P.stage_source(source,'00'*32,bad),bad/'source-helper')
        assert not (bad/'source-helper').exists()

        link=work/'source-symlink';link.symlink_to(source)
        target=directory('source-symlink')
        denied('symlink_source_rejected',lambda:P.stage_source(link,digest,target),target/'source-helper')
        assert not (target/'source-helper').exists()

        target=directory('existing');(target/'source-helper').write_bytes(b'preserve')
        denied('existing_destination_not_overwritten',lambda:P.stage_source(source,digest,target),target/'source-helper')
        assert (target/'source-helper').read_bytes()==b'preserve'

        target=directory('destination-link');(target/'source-helper').symlink_to(source)
        denied('symlink_destination_not_followed',lambda:P.stage_source(source,digest,target),target/'source-helper')
        assert sha256(source.read_bytes()).hexdigest()==digest

        target=directory('loose-mode');target.chmod(0o755)
        denied('nonprivate_directory_rejected',lambda:P.stage_source(source,digest,target),target/'source-helper')
        assert not (target/'source-helper').exists()

        real=directory('real-directory');linkdir=temporary/'linked-directory';linkdir.symlink_to(real,target_is_directory=True)
        denied('symlink_directory_rejected',lambda:P.stage_source(source,digest,linkdir),real/'source-helper')
        assert not (real/'source-helper').exists()

        # Only this test's expendable fixture source changes its name. Original
        # build artifacts and earlier trial records remain untouched.
        source.rename(work/'fixture-source-unavailable')
        jd=work/'internal-source-launch';jd.mkdir(mode=0o700)
        frame=E.Frame(jd/'shared.bin',E.IPC(),block_phase=4)
        stage=jd/'staged-grant'
        body=P.bootstrap_body(good/'source-helper',digest,stage.parent,stage,frame.path,frame.nonce.hex(),fixture=True,lease=stage/'entry.once')
        argv=['/usr/bin/env','-i','PATH=/usr/bin:/bin:/usr/sbin:/sbin','/bin/sh','-c',body]
        job=S.Job._spawn(jd,frame,argv,stage/'helper',mode='fixture')
        state=wait(job,lambda s:s.get('active_native_call_phase')==4)
        cwd=subprocess.check_output(['/usr/sbin/lsof','-a','-p',str(job.identity['pid']),'-d','cwd','-Fn'],text=True)
        assert '\nn/\n' in '\n'+cwd
        pid=job.identity['pid'];job.frame.release_fixture()
        result=wait(job,lambda s:s.get('helper_terminal_verified'))
        assert result['receipt']['fixture_calls'][0:4]==[1,1,1,1]
        assert job.ack_sent and job.frame.grant.native_started==1
        cases.append({'name':'internal_source_fixture_executes_with_external_alias_unavailable_and_cwd_root',
            'helper_pid':pid,'actual_cwd':'/','helper_terminal_verified':True,'status':result['status'],
            'fixture_not_IOKit_or_root':True})

        script,body=P.native_terminal('00'*16)
        assert '/Volumes/' not in script and str(P.LOCAL_SOURCE) in script
        assert 'cd /' in body and 'shasum -a 256' in body
        assert str(P.ROOT_DIR/'helper') in body and '/usr/bin/env -i ' in script
        assert '/usr/bin/sudo -- ' in script and 'osascript' not in script
        cases.append({'name':'reviewed_admin_source_has_only_internal_paths_and_postcopy_hash','admin_executed':False})

        goal=json.loads((HERE.parent/'GOAL_STATUS.json').read_text())
        denied('old_grant_cannot_launch_new_candidate',lambda:P.live_authority(goal),P.JOB_DIR)
        assert not P.JOB_DIR.exists() and not (HERE/'physical-grant-attempt.claim').exists()
        cases.append({'name':'old_consumed_claim_preserved',
            'sha256':sha256((HERE.parent/'stage156-hardened-owner-launch-and-ack/physical-grant-attempt.claim').read_bytes()).hexdigest()})
        cases.append({'name':'consumed_second_claim_preserved',
            'sha256':sha256((HERE.parent/'stage164-internal-staged-owner-launch/physical-grant-attempt.claim').read_bytes()).hexdigest()})
        cases.append({'name':'consumed_third_claim_preserved',
            'sha256':sha256((HERE.parent/'stage166-cross-uid-kernel-identity/physical-grant-attempt.claim').read_bytes()).hexdigest()})
    finally:
        if job is not None:
            if job.relay.poll() is None:
                job.request_stop();job.frame.release_fixture()
                wait(job,lambda s:s.get('helper_terminal_verified'))
            job.frame.terminal=True;job.close_terminal()
    report={'status':'PASS_USER_INTERNAL_STAGING_NOT_ADMIN_OR_USB_ACCEPTANCE','checks':len(cases),
        'cases':cases,'retained_fixture_private_directory':str(temporary),
        'root_or_native_IOKit_execution':False,'administrator_prompt_requested':False,'device_operations':0,
        'script_sha256':sha256(script.encode()).hexdigest(),'bootstrap_sha256':sha256(body.encode()).hexdigest()}
    with (HERE/'internal-stage-tests.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'checks':len(cases),'internal_staging_exercised':True,'root_or_device_operations':0}))


if __name__=='__main__':main()
