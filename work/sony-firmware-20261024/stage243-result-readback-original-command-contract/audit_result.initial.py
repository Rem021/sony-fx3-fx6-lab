"""Seal preparation checks for own C record / offline host decoder evidence."""
from pathlib import Path
from hashlib import sha256
import ast,difflib,json,struct
import entry_build as D
import result_protocol as P
H=Path(__file__).resolve().parent;R=H.parents[2]
def load(p):return json.loads(p.read_text())
def sha(p):return sha256(p.read_bytes()).hexdigest()
t=load(H/'runs-result/receipt.json');assert t['tests']==8 and t['failures']==t['errors']==0 and len(t['cases'])==19
for n,pin in t['source_hashes'].items():assert sha(H/n)==sha(H/'runs-result/source-snapshot'/n)==pin
raw=(H/'build-initial/entry.so').read_bytes();build=load(H/'build-initial/build.json');repro=load(H/'reproducible-build/build.json')
assert raw==(H/'reproducible-build/entry.so').read_bytes()
assert sha256(raw).hexdigest()==t['binary_sha256']==build['sha256']==repro['sha256']=='e009b374283a8f8d0f1c1101f95c5b5d2ec0bd46530440d57f9c94b32ae30232'
assert len(raw)==262144
for folder in ['build-initial','reproducible-build']:
 b=load(H/folder/'build.json')
 for n,pin in b['source_pins'].items():assert sha(H/n)==sha(H/folder/n)==pin
 for n in ['front','bridge','parent','collector']:assert not (H/folder/(n+'.o.stderr.txt')).read_bytes()
assert D.inspect_dynamic(raw,build['global_offsets']['fx3_entry_init'])==build['dynamic_inspection']
inverse={v:k for k,v in D.RELOCATIONS.items()};deltas=[0,0x20000000,0x30000000,0x50010000,0x60000000]
for x in build['relocations']:
 assert struct.unpack_from('<I',raw,x['file_offset'])[0]==x['after']
 for delta in deltas:assert D.relocate(x['before'],inverse[x['kind']],x['place']+delta,x['target']+delta)==x['after']
assert len(build['relocations'])==231
expected=P.Expected.from_artifact(raw,pinned_file_sha=sha256(raw).digest(),nonce=b'\xbb'*16,profile=b'\xcc'*32,controller=b'\xdd'*32)
rows={x['name']:x for x in t['cases']};model_rows=[x for x in t['cases'] if 'summary' in x];assert len(model_rows)==16
for r in model_rows:
 s=r['summary'];assert not s['source_accesses'] and not s['root_remaining_new_FDs'] and not s['root_remaining_anonymous']
 assert s['borrowed_FDs_unchanged'] and not s['native_GET_or_USB_transport_executed']
for name in ['normal-321','normal-9011']:
 s=rows[name]['summary'];assert s['result']==11 and s['collector_status']==10752 and s['worker_status']==0
 p=bytes.fromhex(s['result_record_hex']);out=P.decode_native_body(bytes(4)+p,expected)
 assert len(p)==256 and out['reported_core_status']==11 and not out['may_release_owner_or_flash']
for name in ['fsync','readback','close','owner-close','root-close','expire-after-close']:
 s=rows['result-'+name]['summary'];out=P.decode_native_body(bytes(4)+bytes.fromhex(s['result_record_hex']),expected)
 assert s['result']==2 and out['reported_core_status']==11 and not out['report_close_setter_return_USB_or_full_job_completion_proven']
for name in ['open','short-write','existing']:
 s=rows['result-'+name]['summary'];assert s['result']==2
native=load(H/'native-result-contract.json');assert native['complete_functions']==12 and native['instruction_checks']==56
assert len(native['jump_tables'])==2 and sum(len(x['rows']) for x in native['jump_tables'])==21
assert not native['original_Sony_or_downloaded_code_executed'] and native['new_device_USB_cache_admin_auth_upload_or_firmware_operations']==0
assert sha(R/native['original_source'])==native['original_source_sha256']
for x in native['checks']:
 fns=load(H/'original-functions.json')['functions']+[load(H/'original-path-selector.json')]+load(H/'original-dispatch-functions.json')
 assert any(i['pc']==x['pc'] and i['word']==x['word'] for f in fns for i in f['instructions'])
for o in load(H/'candidate-source-origins.json'):assert sha(R/o['path'])==o['sha256']
assert load(H/'native-audit-initial-failure.json')['status']=='INITIAL_STATIC_TABLE_EXPECTATION_FAILED'
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
report=dict(status='OWN_LOCAL_RECORD_PINNED_DECODER_AND_STATIC_READ_CONTRACT_PASS_NOT_DEVICE_ADMISSION',
 own_checks=8,own_ARM64_model_runs=16,receipt_rows=19,host_rejection_variants=28,
 full_file_sha256=build['sha256'],immutable_image_id=build['immutable_image_id'],ELF_bytes=262144,
 link_relocations=231,rebase_arithmetic_checks=1155,native_full_functions=12,native_instruction_checks=56,dispatch_entries=21,
 test_source_hashes=t['source_hashes'],
 late_publication_failure_with_valid_core11_record_retained=True,
 decoder_output_is_reported_local_observation_not_authenticated_completion=True,
 inner_frames_fixed_but_actual_DMM_auth_path_ownership_namespace_and_native_reply_unverified=True,
 original_Sony_Linux_glibc_or_downloaded_code_executed=False,new_device_operations=0,
 full_boot_backup_independent_AP_restore_MAIN_HEVC_or_first_flash_verified=False,
 probe_deployable=False,first_flash_released=False)
(H/'candidate-audit.json').open('x').write(json.dumps(report,indent=2)+'\n')
diff=''.join(difflib.unified_diff((H/'front.before-result.c').read_text().splitlines(True),(H/'front.c').read_text().splitlines(True),fromfile='242/front.c',tofile='243/front.c'))
history=dict(front_diff=diff,seed_generation=load(H/'result-source-extension.json'),
 native_audit_initial_expected_GET_branch_was_b1fc_actual_table_target_is_b1f8=True,
 four_byte_annotation_correction_not_camera_or_firmware_fault=True,
 native_auditor_before_sha256=sha(H/'audit_native_contract.initial.py'),native_auditor_current_sha256=sha(H/'audit_native_contract.py'))
(H/'source-revisions.json').open('x').write(json.dumps(history,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],own_checks=8,ARM64_runs=16,host_rejection_variants=28,native_checks=56)))
