"""Real user shell/child IO only; privileged example is never executed."""
from pathlib import Path
from hashlib import sha256
import difflib
import importlib.util
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
from receipt_channel import render_user_channel

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'stage173-Terminal-owner-launch-and-login-guard'

def main():
    root=Path(tempfile.mkdtemp(prefix='fx3-receipt-channel-fixture-',dir='/private/tmp'))
    assert root.stat().st_uid==501 and stat.S_IMODE(root.stat().st_mode)==0o700
    cases=[];q=lambda s:shlex.quote(str(s))
    def make(name,code):
        d=root/name;d.mkdir(mode=0o700)
        counter=d/'child.calls'
        payload="import os,json,sys; p="+repr(str(counter))+"; f=open(p,'a'); f.write('one\\n'); f.close(); "+code
        # Only self-owned Python fixture is executed; no sudo, native helper,
        # IOKit or Terminal application occurs in this invocation.
        body='exec '+q(sys.executable)+' -B -c '+q(payload)+' 2>&1'
        invocation='/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c '+q(body)
        script=render_user_channel(invocation,d,'fx3-receipt-fixture-01','01'*16)
        assert '/usr/bin/sudo' not in script and '/var/root/' not in script
        path=d/'fixture.sh';path.write_text(script)
        return d,path,counter
    def run(path):return subprocess.run(['/bin/sh',str(path)],capture_output=True,text=True)

    d,path,counter=make('normal',"print(json.dumps({'fixture':True,'uid':os.getuid(),'euid':os.geteuid()}))")
    result=run(path);assert result.returncode==0
    output=d/'relay-stdout.txt';st=output.stat();value=json.loads(output.read_text())
    assert st.st_uid==501 and stat.S_IMODE(st.st_mode)==0o600 and value['uid']==value['euid']==501
    assert counter.read_text()=='one\n'
    marker=json.loads((d/'terminal-command-result.json').read_text());assert marker['returncode']==0
    cases.append({'name':'outer_user_redirection_owns_private_result_and_completion','uid':st.st_uid,'mode':oct(stat.S_IMODE(st.st_mode))})

    digest=sha256(output.read_bytes()).hexdigest();marker_digest=sha256((d/'terminal-command-result.json').read_bytes()).hexdigest()
    result=run(path);assert result.returncode!=0 and counter.read_text()=='one\n'
    assert sha256(output.read_bytes()).hexdigest()==digest and sha256((d/'terminal-command-result.json').read_bytes()).hexdigest()==marker_digest
    cases.append({'name':'repeat_wrapper_does_not_execute_child_or_overwrite_results'})

    d,path,counter=make('child-failure',"print('fixture-child-error',file=sys.stderr); sys.exit(23)")
    result=run(path);assert result.returncode==23
    assert (d/'relay-stdout.txt').read_text().strip()=='fixture-child-error'
    assert json.loads((d/'terminal-command-result.json').read_text())['returncode']==23
    assert result.stderr=='' and (d/'relay-stdout.txt').stat().st_uid==501
    cases.append({'name':'child_stderr_can_join_user_channel_without_redirecting_wrapper_verification_stderr','exit':23})

    d,path,counter=make('destination-symlink',"print('must-not-execute')")
    target=d/'preserve.txt';target.write_text('preserve');(d/'relay-stdout.txt').symlink_to(target)
    result=run(path);assert result.returncode!=0 and target.read_text()=='preserve' and not counter.exists()
    cases.append({'name':'noclobber_rejects_existing_or_symlink_result_before_child'})

    # Derive a review patch, never modify the consumed release. The existing
    # actual172 root run supplies cross-UID evidence; these new tests are user IO.
    sys.path.insert(0,str(SOURCE));import launch_policy as P
    old=(SOURCE/'launch_policy.py').read_text()
    needle="' > '+q(JOB_DIR/'relay-stdout.txt')+' 2> '+q(JOB_DIR/'relay-stderr.txt')+'\\n'"
    assert old.count(needle)==1
    repaired=old.replace(needle,"' 2>&1\\n'",1)
    needle2="+q(body)+'; then',"
    assert repaired.count(needle2)==1
    repaired=repaired.replace(needle2,"+q(body)+' > '+q(JOB_DIR/'relay-stdout.txt')+'; then',",1)
    patch=''.join(difflib.unified_diff(old.splitlines(True),repaired.splitlines(True),fromfile='173/launch_policy.py (consumed; unchanged)',tofile='future-fixed-release/launch_policy.py (review only)'))
    (HERE/'launch_policy.user-stdout.REVIEW_ONLY.patch').write_text(patch)
    namespace={'__file__':str(SOURCE/'launch_policy.py'),'__name__':'offline_repaired_preview'}
    exec(compile(repaired,'review-only-launch-policy','exec'),namespace)
    command,body=namespace['native_terminal']('01'*16)
    assert body.splitlines()[-1].endswith(' 2>&1') and 'relay-stdout.txt' not in body and 'relay-stderr.txt' not in body
    assert "' > /private/tmp/" in command and 'relay-stdout.txt; then' in command
    assert 'sudo -- /usr/bin/env -i ' in command and 'sudo -S' not in command and 'sudo -A' not in command
    # A hard stop prevents accidental execution of this historical-grant example.
    example=HERE/'fixed-channel-example.REVIEW_ONLY.sh'
    example.write_text('#!/bin/sh\nexit 64 # REVIEW ONLY: consumed05, no live release\n'+command)
    subprocess.run(['/bin/sh','-n',str(example)],check=True,capture_output=True)
    cases.append({'name':'derived_fixed_preview_uses_user_stdout_only_and_keeps_sudo_verification_stderr_in_Terminal','example_executed':False})

    result=subprocess.run([sys.executable,'-B',str(HERE/'receipt_channel.py')],check=True,capture_output=True,text=True)
    assert json.loads(result.stdout)['state']=='PLAN_ONLY_OFFLINE_RECEIPT_CHANNEL'
    assert (SOURCE/'launch_policy.py').read_text()==old
    cases.append({'name':'default_generator_cannot_launch_or_apply_to_consumed05'})

    report={'status':'PASS_OFFLINE_USER_STDOUT_CHANNEL_NOT_NEW_ROOT_OR_CAMERA_TEST','checks':len(cases),'cases':cases,
        'retained_fixture_directory':str(root),'actual_new_root_or_sudo_or_Terminal_or_IOKit_execution':False,
        'existing173_sources_unchanged':True,'camera_operations':0,'cross_uid_limit':'Fresh fixtures use UID501 only. Prior actual172 UID0 output in UID501/0600 file is separate existing evidence.'}
    with (HERE/'receipt-channel-tests.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'receipt_channel_checks':len(cases),'new_root_or_camera_operations':0,'consumed173_unchanged':True}))

if __name__=='__main__':main()
