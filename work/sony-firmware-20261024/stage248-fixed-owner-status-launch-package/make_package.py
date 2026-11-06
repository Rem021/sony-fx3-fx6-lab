"""Freeze reviewable scope and executable hashes; no staging or launch."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess
import controller_ipc as I
import fixed_launch as P
import receipt_receiver as R
H=Path(__file__).resolve().parent
material=json.loads((H/'fixed-material.json').read_text());build=I.build();nonce=material['nonce']
command,body=P.render_native(nonce)
q=subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True,timeout=2);assert q.returncode==0,q.stderr
plan=dict(schema=1,created_utc=datetime.now(timezone.utc).isoformat(),grant_id=R.GRANT_ID,scope='MSC_OWNER_STATUS_ONLY',
 authorized=False,executed=False,maximum_helper_invocations=1,
 nonce=nonce,target=material['target'],privacy_key_source='fixed-material.json; root-private cached-serial HMAC consistency only',
 expected_console_uid=501,expected_helper_uid=0,job=str(P.JOB),root_base=str(P.ROOT_BASE),root_grant_directory=str(P.ROOT_DIR),
 helper_sha256=build['builds']['native']['sha256'],permit_sha256=material['permit_sha256'],permit_bytes=96,
 terminal_command_sha256=sha256(command.encode()).hexdigest(),
 host_control_ops=['OBSERVE','STATUS','END'],Sony_control_bulk_file_firmware_commands=0,
 usb_capture_and_return=True,may_temporarily_disconnect_storage_driver=True,
 camera_all_volumes_must_be_manually_ejected=True,keep_current_port_and_MSC=True,
 work_budget_ms=20000,final_observation_budget_ms=30000,blocking_calls_not_forcibly_interruptible=True,
 auto_retry_reset_kill_or_mode_fallback=False,privacy_permission_changes=False,
 root_helper_new_files=['helper:0500','permit.bin:0400','entry.once:0400'],
 shared_global_guard=str(P.ROOT_BASE/'global-fx3-owner.journal'),
 does_not_authorize_authentication_module_upload_backup_restore_recording_or_flash=True)
for name,data in [('fixed-plan.json',(json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode()),
 ('OwnerStatus.command.txt',command.encode()),('root-body-render-only.sh.txt',body.encode())]:
 with (H/name).open('xb') as f:f.write(data)
files=[p for p in H.iterdir() if p.suffix in ('.c','.h') and '.initial.' not in p.name]
files += [H/n for n in ('controller_ipc.py','receipt_receiver.py','supervisor.py','fixed_launch.py','native_factory.py','run_approved_status.py','cache_parser.py',
 'README.md','fixed-material.json','fixed-plan.json','permit.bin','build-receipt.json','OwnerStatus.command.txt','root-body-render-only.sh.txt')]
files += [Path(x['path']) for x in build['builds'].values()]
bundle=dict(schema=1,grant_id=R.GRANT_ID,scope='MSC_OWNER_STATUS_ONLY',maximum_helper_invocations=1,
 approved=False,executed=False,root_private_fixed_permit_required=True,Sony_auth_file_or_firmware_commands=0,
 files=[dict(path=str(p.relative_to(H)),bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest()) for p in sorted(set(files))])
raw=(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode()
with (H/'approval-bundle.json').open('xb') as f:f.write(raw)
print(json.dumps(dict(approval_bundle_sha256=sha256(raw).hexdigest(),helper_sha256=plan['helper_sha256'],files=len(bundle['files']),executed=False)))
