"""Two nonexecuting approval/runtime-layout checks. No root or fixed job IO."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from unittest.mock import patch
import json,os,subprocess
import host_plan as P
import host_supervisor as S
import receipt_receiver as R
HERE=Path(__file__).resolve().parent
bundle,digest=P.checked_bundle();plan=json.loads((HERE/'fixed-plan.json').read_text())
before_job=os.path.lexists(P.JOB)
base={'authorization':{'Mac_root_host01':{'authorized':True,'grant_id':R.GRANT_ID,'bundle_sha256':digest,'scope':'HOST_ONLY','maximum_helper_invocations':2}}}
assert P.authority(base)==bundle # policy model only; no prepare/launch
def must_reject(goal):
    try:P.authority(goal)
    except R.Rejected:return
    raise AssertionError('nonexact authorization accepted')
for key,value in (('authorized',1),('authorized',False),('grant_id','old05'),('bundle_sha256','0'*64),('scope','CAMERA'),('maximum_helper_invocations',2.0),('maximum_helper_invocations',3)):
    item=deepcopy(base);item['authorization']['Mac_root_host01'][key]=value;must_reject(item)
old=json.loads((HERE/'goal-status-before.json').read_text())
must_reject(old)
with patch.object(Path,'mkdir',side_effect=AssertionError('staging before authorization')),patch.object(subprocess,'Popen',side_effect=AssertionError('process before authorization')):
    try:S.prepare_root_session(old)
    except R.Rejected:pass
    else:raise AssertionError('old authority prepared root job')
assert os.path.lexists(P.JOB)==before_job

class FakeFrame:
    def __init__(self,path,ipc,nonce=None):self.path=Path(path);self.nonce=nonce
class FakeSocket:
    def __init__(self,*args):pass
    def bind(self,path):self.path=Path(path)
    def listen(self,n):pass
    def setblocking(self,flag):pass
j=S.Session();j.directory=P.JOB;j.sockdir=P.JOB;j.ipc=object()
with patch.object(S.I,'Frame',FakeFrame),patch.object(S.socket,'socket',FakeSocket),patch.object(S.os,'chmod',lambda *args:None):j._stages(plan['nonces'])
assert [s.frame.path for s in j.stages]==[P.JOB/'trial.bin',P.JOB/'query.bin']
assert [s.frame.nonce.hex() for s in j.stages]==plan['nonces']
assert j.sockpaths==[P.JOB/'trial.sock',P.JOB/'query.sock']
script=P.body(P.JOB/'source-helper',plan['root_helper_sha256'],P.JOB,P.PROTECTED,plan['nonces'],j.sockpaths)
command=P.command(script,P.JOB)
assert sha256(command.encode()).hexdigest()==plan['terminal_command_sha256']
assert command==(HERE/'RootHostValidation.command.txt').read_text()
check=subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True,timeout=2);assert check.returncode==0,check.stderr
assert os.path.lexists(P.JOB)==before_job
report={'status':'PASS_EXACT_HOST_APPROVAL_AND_LAYOUT','tests_run':2,'authorization_models_do_not_launch':True,
        'old_grants_rejected_before_staging_or_process':True,'actual_root_job_created':False,'actual_root_candidate_executed':False,
        'root_or_device_operations':0,'runtime_layout_uses_mocks_explicit':True,'shell_syntax_only':True,
        'bundle_sha256':digest,'test_source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'plan_source_sha256':sha256((HERE/'host_plan.py').read_bytes()).hexdigest(),
        'supervisor_source_sha256':sha256((HERE/'host_supervisor.py').read_bytes()).hexdigest()}
S.put(HERE/'approval-boundary-results.json',report);print(json.dumps(report))
