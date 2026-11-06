"""Create reviewable fixed plan/bundle only. Never stage or execute root job."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,secrets,subprocess
import host_plan as P
import controller_ipc as I
HERE=Path(__file__).resolve().parent
b=I.build();root=b['builds']['root_host'];nonces=[secrets.token_hex(16),secrets.token_hex(16)]
script=P.body(P.JOB/'source-helper',root['sha256'],P.JOB,P.PROTECTED,nonces,[P.JOB/'trial.sock',P.JOB/'query.sock'])
command=P.command(script,P.JOB)
checked=subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True,timeout=2)
assert checked.returncode==0,checked.stderr
plan={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),'grant_id':P.R.GRANT_ID,'scope':'HOST_ONLY',
      'expected_console_uid':501,'expected_helper_uid':0,'maximum_helper_invocations':2,
      'invocations':['trial','readback'],'nonces':nonces,'root_helper_sha256':root['sha256'],
      'terminal_command_sha256':sha256(command.encode()).hexdigest(),'job_directory':str(P.JOB),
      'root_base':str(P.BASE),'root_grant_directory':str(P.PROTECTED),'root_helper_path':str(P.PROTECTED/'helper'),
      'root_new_files':{'helper':'0500','trial.once':'0400','readback.once':'0400','host-only.journal':'0600','host-result.bin':'0600'},
      'camera_USB_driver_auth_firmware_operations':0,'privacy_or_audit_permission_changes':False,
      'automatic_retry_or_kill':False,'approved_or_executed':False,
      'persistence_scope':'fsync and checksum/current protected readback; no sudden-power-loss, APFS-crash or camera-recovery proof'}
for name,data in (('fixed-plan.json',(json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode()),
                  ('root-body-render-only.sh.txt',script.encode()),('RootHostValidation.command.txt',command.encode())):
 with (HERE/name).open('xb') as f:f.write(data)
files=[p for p in sorted(HERE.iterdir()) if p.suffix in ('.c','.h','.py') and not p.name.startswith('test_') and p.name not in ('make_plan.py',)]
files+=[HERE/'README.md',HERE/'fixed-plan.json',HERE/'root-body-render-only.sh.txt',HERE/'RootHostValidation.command.txt',HERE/'build-receipt.json',Path(root['path']),Path(b['builds']['ipc']['path'])]
bundle={'schema':1,'grant_id':P.R.GRANT_ID,'scope':'HOST_ONLY','maximum_helper_invocations':2,
        'admin_execution_approved':False,'root_candidate_executed':False,'no_device_backend':True,
        'files':[{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()} for p in sorted(set(files))]}
raw=(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'approval-bundle.json').open('xb') as f:f.write(raw)
print(json.dumps({'bundle_sha256':sha256(raw).hexdigest(),'root_helper_sha256':root['sha256'],'invocations_max':2,'root_executed':False}))
