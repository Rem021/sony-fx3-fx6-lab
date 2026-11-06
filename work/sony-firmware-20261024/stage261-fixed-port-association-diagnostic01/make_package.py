"""Freeze source/commands after build; no staging, device or privilege calls."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,subprocess
import controller_ipc as I
import fixed_launch as P
import receipt_receiver as R
H=Path(__file__).resolve().parent
def put(name,value):
    data=value if isinstance(value,bytes) else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
    with(H/name).open('xb') as f:f.write(data)
material=json.loads((H/'fixed-material.json').read_text());build=I.build()
command,body=P.render_native(material['nonce'])
p=subprocess.run(['/bin/sh','-n'],input=command,text=True,capture_output=True,timeout=2);assert p.returncode==0,p.stderr
plan=dict(schema=2,created_utc=datetime.now(timezone.utc).isoformat(),grant_id=R.GRANT_ID,scope=P.SCOPE,
    authorization_source='user explicit continuing research/all-agree instruction; exact local scope binding required before launch',
    maximum_helper_invocations=1,executed=False,target=material['target'],nonce=material['nonce'],
    physical_port_registryID=material['physical_port_registryID'],physical_custody_no_substitution_assumption=True,
    association_basis='bounded sampled physical USB-C port; not cryptographic identity or complete event capture',
    maximum_transition_window_ms=2000,maximum_samples_per_transition=20,
    expected_console_uid=501,expected_helper_uid=0,job=str(P.JOB),root_directory=str(P.ROOT_DIR),
    helper_sha256=build['builds']['native']['sha256'],permit_sha256=material['permit_sha256'],
    terminal_command_sha256=sha256(command.encode()).hexdigest(),
    camera_all_volumes_must_be_ejected=True,USB_capture_and_return=True,
    MSC_authentication_exchanges=7,SERVICE_authentication_exchanges_if_descriptor_matches=7,
    fixed_read0_command_count_if_matches=1,fixed_read0_max_body_bytes=88,
    control_only_mismatch_exit_experimental=True,save_raw_Hasp_or_authentication=False,
    authentication_may_change_history_or_mode=True,zero_camera_writes_claimed=False,
    root_private_files=['helper:0500','permit.bin:0400','entry.once:0400','private-flow.bin:0400'],
    work_budget_ms=20000,final_budget_ms=30000,blocking_calls_not_forcibly_interruptible=True,
    auto_retry_reset_kill_or_identity_fallback=False,firmware_write=False,module_upload=False,
    global_guard=str(P.ROOT_BASE/'global-fx3-owner.journal'),
    global_camera_state_after_Sony_commands='UNKNOWN even nominal host return',
    no_camera_backup_or_recovery_guarantee=True,physical_camera_acceptance=False)
put('fixed-plan.json',plan);put('SonyCommunication.command.txt',command.encode());put('root-body-render-only.sh.txt',body.encode())
files=[p for p in H.iterdir() if p.is_file() and p.suffix in ('.c','.h','.inc','.py')]
files += [H/n for n in ('README.md','upstream-LICENSE.txt','fixed-material.json','fixed-plan.json','permit.bin','build-receipt.json','SonyCommunication.command.txt','root-body-render-only.sh.txt')]
files += [Path(x['path']) for x in build['builds'].values()]
bundle=dict(schema=2,grant_id=R.GRANT_ID,scope=P.SCOPE,maximum_helper_invocations=1,
    physical_port_registryID=material['physical_port_registryID'],
    firmware_write=False,module_upload=False,authentication_may_change_history_or_mode=True,
    files=[dict(path=str(p.relative_to(H)),bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest()) for p in sorted(set(files))])
put('approval-bundle.json',bundle)
print(json.dumps(dict(status='FIXED_COMMUNICATION_PACKAGE_RENDERED_NOT_STAGED',bundle_sha256=sha256((H/'approval-bundle.json').read_bytes()).hexdigest(),helper_sha256=plan['helper_sha256'],files=len(bundle['files']),executed=False)))
