"""Bound the own candidate and its evidence. Never invoke a native loader."""
from pathlib import Path
from hashlib import sha256
import ast,difflib,json,struct
import entry_build as D
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
def load(p):return json.loads(p.read_text())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
 with (H/n).open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
t=load(H/'runs-v2/receipt.json');assert t['tests']==9 and len(t['cases'])==44 and t['errors']==t['failures']==0
assert t['status']=='OWN_DT_INIT_PREPARATION_AND_CROSS_LOAD_CLAIM_SCOPED_PASS'
for n,pin in t['source_hashes'].items():assert sha(H/n)==sha(H/'runs-v2/source-snapshot'/n)==pin
raw=(H/'build-v2/entry.so').read_bytes();build=load(H/'build-v2/build.json');again=load(H/'reproducible-v2/build.json')
assert raw==(H/'reproducible-v2/entry.so').read_bytes()
assert sha256(raw).hexdigest()==build['sha256']==again['sha256']==t['binary_sha256']=='e6fc7398b05939c40150471c216ddef2e0a15c9cf01d6c0d83ccebd6218807ff'
assert build['immutable_image_id']==again['immutable_image_id']==t['immutable_image_id']==sha256(raw[:3*D.PAGE]+bytes(D.PAGE)).hexdigest()
assert build['immutable_image_id']!=build['sha256']
for folder in ['build-v2','reproducible-v2']:
 b=load(H/folder/'build.json');assert b['source_pins']==build['source_pins']
 for n,pin in b['source_pins'].items():assert sha(H/n)==sha(H/folder/n)==pin
 for n in ['parent','collector','bridge','front']:assert not (H/folder/(n+'.o.stderr.txt')).read_bytes()
dynamic=D.inspect_dynamic(raw,build['global_offsets']['fx3_entry_init'])
assert dynamic['no_DT_NEEDED_or_dynamic_exports_or_runtime_relocations']
rejections=[]
for name,offset,value in [('NEEDED-tag',3*D.PAGE,1),('other-init',3*D.PAGE+5*16+8,dynamic['DT_INIT']+4),('symbol-table-byte',8208,1)]:
 data=bytearray(raw)
 if name=='symbol-table-byte':data[offset]=value
 else:struct.pack_into('<Q',data,offset,value)
 try:D.inspect_dynamic(bytes(data),build['global_offsets']['fx3_entry_init'])
 except ValueError:rejections.append(name)
 else:raise AssertionError('modified dynamic metadata accepted '+name)
inverse={v:k for k,v in D.RELOCATIONS.items()};deltas=[0,0x20000000,0x30000000,0x50010000,0x60000000]
for x in build['relocations']:
 assert struct.unpack_from('<I',raw,x['file_offset'])[0]==x['after']
 for delta in deltas:
  assert delta%D.PAGE==0 and D.relocate(x['before'],inverse[x['kind']],x['place']+delta,x['target']+delta)==x['after']
assert len(build['relocations'])==215
refs=[]
def reference(path,first,last,tokens,url):
 p=B/path;lines=p.read_text().splitlines(keepends=True);part=''.join(lines[first-1:last]);assert all(s in part for s in tokens)
 refs.append(dict(path=str(p.relative_to(R)),sha256=sha(p),first_line=first,last_line=last,
                  range_sha256=sha256(part.encode()).hexdigest(),required_tokens=tokens,url=url))
reference('stage230-constructor-child-entry-portability/reference/glibc-2.25-dl-init.c',53,74,
 ['DL_CALL_DT_INIT','l->l_addr + l->l_info[DT_INIT]->d_un.d_ptr','argc, argv, env','DT_INIT_ARRAY'],
 'https://github.com/bminor/glibc/blob/glibc-2.25/elf/dl-init.c')
namei='stage234-fixed-RAM-plan-preparer/source-reference/namei.c';url='https://github.com/torvalds/linux/blob/v4.9/fs/namei.c'
reference(namei,3602,3610,['LOOKUP_CREATE | LOOKUP_EXCL','inode_lock_nested','-EEXIST','d_is_positive'],url)
reference(namei,3649,3663,['done_path_create','inode_unlock','user_path_create','filename_create'],url)
reference(namei,3785,3811,['SYSCALL_DEFINE3(mkdirat','user_path_create','vfs_mkdir','done_path_create'],url)
reference('stage234-fixed-RAM-plan-preparer/source-reference/unistd.h',121,124,['__NR_mkdirat 34','sys_mkdirat'],
 'https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/unistd.h')
changes={}
for n,seed in [('front.c','front.c.pre-planv2'),('bridge.c','bridge.c.pre-planv2'),('bridge_job.h','bridge_job.h.pre-planv2'),('entry_build.py','entry_build.pre-metadata-clarification.py')]:
 changes[n]=dict(before_sha256=sha(H/seed),current_sha256=sha(H/n),before_path=seed,
                 diff=''.join(difflib.unified_diff((H/seed).read_text().splitlines(True),(H/n).read_text().splitlines(True),fromfile=seed,tofile=n)))
initial=load(H/'runs-integrated/receipt.json');assert initial['failures']==1 and initial['errors']==0
oldcases={x['name']:x['summary'] for x in initial['cases']};assert oldcases['image-file']['result']==11
for folder in ['runs-integrated','runs-verified']:
 receipt=load(H/folder/'receipt.json')
 for n,pin in receipt['source_hashes'].items():assert sha(H/folder/'source-snapshot'/n)==pin
assert load(H/'runs-verified/receipt.json')['failures']==0
for x in load(H/'source-origins.json'):assert sha(R/x['path'])==x['sha256']
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
put('source-revisions.json',dict(changes=changes,seed_generator_outputs_protocol_plan1_IPC3_not_current_plan2_IPC4=True,
 current_build_uses_current_pinned_C_not_seed_generator_output=True,
 initial_failure_was_wrong_test_injection_address_in_unhashed_RW_page=True,
 immutable_file_mismatch_now_injected_at_196607=True,
 mutable_padding_boundary_retained_and_full_file_SHA_bound_in_plan2_and_IPC4=True,
 metadata_only_builder_clarification_did_not_change_initial_ELF=True))
put('candidate-audit.json',dict(status='OWN_DYNAMIC_ENTRY_PLAN2_IPC4_CLAIM_SCOPED_PASS_NOT_DEVICE_ADMISSION',
 tests=9,model_cases=44,bytes=len(raw),full_file_sha256=build['sha256'],immutable_image_id=build['immutable_image_id'],
 dynamic=dynamic,malformed_dynamic_rejections=rejections,link_relocations=215,uniform_rebase_arithmetic_checks=215*len(deltas),
 source_ranges=refs,test_source_hashes=t['source_hashes'],
 actual_Linux_mkdir_namespace_or_glibc_Sony_loader_executed_or_verified=False,
 original_im_bytes_read_and_hashed_not_executed=True,
 global_claim_proof_conditional_on_shared_writable_tmpfs_same_root_namespace_and_no_external_removal=True,
 full_file_digest_binding_is_integrity_not_authenticated_request=True,
 no_device_USB_cache_admin_auth_upload_driver_card_or_firmware_operation=True,
 full_boot_capture_host_completion_independent_AP_restore_and_MAIN_HEVC_verified=False,
 first_flash_released=False,probe_deployable=False))
print(json.dumps(dict(status='PASS',tests=9,cases=44,refs=len(refs),relocation_checks=1075,full_file_sha256=build['sha256'])))
