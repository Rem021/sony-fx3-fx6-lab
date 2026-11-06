"""Verify changed source/build/test bindings without executing a device backend."""
from pathlib import Path
from hashlib import sha256
import json,difflib
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];T=B/'stage195-root-host-validation-plan'
current=json.loads((H/'build-receipt-current-port.json').read_text())
for row in current['sources']:assert sha256((H/row['path']).read_bytes()).hexdigest()==row['sha256']
for row in current['builds'].values():assert sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
transport=(H/'host_transport.c').read_text().replace('#ifndef FX3_OWNER_CHANNEL_FIXTURE','#ifndef HOST_FIXTURE')
assert transport==(T/'host_transport.c').read_text()
extra='\n#ifdef FX3_OWNER_CHANNEL_FIXTURE\n    void (*before_request)(void *);\n    void *fixture;\n#endif'
assert (H/'host_transport.h').read_text().replace(extra,'')==(T/'host_transport.h').read_text()
for name in ('helper_hello.c','host_login.c'):assert (H/name).read_bytes()==(T/name).read_bytes()
channel=(H/'owner_channel.c').read_text();receipt=(H/'owner_receipt.c').read_text()
assert 'int fx3_channel_peer(' not in channel and 'int fx3_channel_connect(' not in channel
assert 'int fx3_receipt_peer_ack(' not in receipt and 'int fx3_receipt_send_bytes(' not in receipt
assert 'cfg->scope!=1' in channel and 'if(op!=FX3S_OBSERVE && op!=FX3S_STATUS && op!=FX3S_END)' in channel
assert '#define FX3_NATIVE_RELEASED 0' in (H/'entry_target.h').read_text()
assert 'raise R.Rejected' in (H/'fixed_launch.py').read_text().split('def native_authority(')[1]
tests=json.loads((H/'integration-receipt.json').read_text());ports=json.loads((H/'current-port-verification.json').read_text())
assert tests['checks']==8 and ports['checks']==2
assert all(x['status']=='PASS' and x['wire_calls']==[0,0,0] for x in tests['rows']+ports['rows'])
cache=json.loads((H/'current-cache-target.json').read_text());assert cache['candidate_count']==1
assert cache['candidates'][0]['locationID']==0x01100000
assert '#define FX3_FIXED_LOCATION 0x01100000u' in (H/'target_binding.h').read_text()
revisions=[]
for row in json.loads((H/'source-origins.json').read_text()):
 src=R/row['source'];assert sha256(src.read_bytes()).hexdigest()==row['source_sha256']
 new=(H/row['path']).read_text();old=src.read_text()
 revisions.append(dict(path=row['path'],original_source=row['source'],source_sha256=row['source_sha256'],
  final_sha256=sha256(new.encode()).hexdigest(),diff=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True)))))
with (H/'source-final-revisions.json').open('x') as f:json.dump(revisions,f,ensure_ascii=False,indent=2);f.write('\n')
plan=dict(schema='fx3-owner-status-only-diagnostic-draft-v1',status='DRAFT_NOT_RELEASED',
 goal='Observe-only owner acquisition and return; no Sony command or firmware modification.',
 source_grant_id='fx3-702-owner-status-20261030-11',authorized=False,native_entry_released=False,
 target=dict(VID='054C',PID='0DA1',model='ILME-FX3',location_hex='0x01100000',
  registryID=cache['candidates'][0]['registryID'],cache_only=True,firmware_hash_verified=False,
  registry_ID_not_yet_a_runtime_admission_pin=True,private_same_unit_tag_materialized=False),
 host_commands=[dict(opcode=1,name='OBSERVE'),dict(opcode=6,name='STATUS'),dict(opcode=5,name='END')],
 allowed_USB_vendor_control_or_bulk_transfers=0,
 root_helper_invocations_proposed_max=1,work_budget_ms=20000,final_observation_budget_ms=30000,
 budgets_cannot_interrupt_blocked_calls=True,
 proposed_flow=['validate new fixed approval, root installation and live parent identity',
  'HELLO self-image and parent ACK before owner actions',
  'verify current target, no mounted/unknown camera media',
  'explicit one-time capture may disconnect the storage driver',
  'claim interface0 and verify81/02 bulk endpoint to pipe mapping',
  'OBSERVE, STATUS, END are local owner commands; no Sony USB request',
  'close interface, release captured device, close device, verify same-target driver baseline',
  'deliver private live result and independently observe original helper exit'],
 outstanding_before_any_execution=['implement native frame preparation and root supervisor factory; current factory always denies',
  'replace fixture-only target tags with explicit same-unit binding and current-target admission',
  'freeze new one-time build/nonce/package and obtain its specific administrator plus USB capture/return approval'],
 on_inflight_or_unknown='retain original process/context, no forced kill/reset/retry or fabricated success',
 success_is_not_camera_authentication_backup_restore_MAIN_HEVC_or_first_flash=True,
 previous195_HOST_ONLY_authorization_consumed_and_not_reused=True)
with (H/'diagnostic-plan.json').open('x') as f:json.dump(plan,f,ensure_ascii=False,indent=2);f.write('\n')
report=dict(status='SHARED_HOST_TRANSPORT_AND_STATUS_ONLY_OWNER_INTEGRATION_SCOPED_PASS',
 root_validated_source='stage246 HOST_ONLY actual execution of fixed195 code',
 shared_transport_native_policy_text_identical_except_test_macro=True,
 helper_HELLO_and_login_sources_byte_identical_to195=True,
 changed_integration_checks=8,current_location_smoke_checks=2,
 new_cache_queries=1,camera_interface_opens_or_camera_commands=0,new_administrator_executions=0,
 current_port='0x01100000',native_built=True,native_executed=False,native_released=False,
 firmware_backup_restore_or_actual_driver_return_validated=False,milestone2_complete=False,
 source_history_preserved=['initial-integration-sources.zip','build-receipt.json','build-receipt-current-port.json'],
 external_primary_source='https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getpeereid.3.html',
 source_interpretation='Peer effective UID/GID come from the connected UNIX socket; current incarnation and self-image are separate checks.')
with (H/'integration-review.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=report['status'],integration_checks=8,current_port_checks=2,cache_queries=1,new_admin_or_camera_commands=0)))
