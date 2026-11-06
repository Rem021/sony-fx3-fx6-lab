"""Register the fixed first-shell filter evidence without new device authority."""
from pathlib import Path
from hashlib import sha256,sha1
from copy import deepcopy
from datetime import datetime,timezone
from io import BytesIO
import ast,json,os,plistlib,re,stat,struct,subprocess,sys
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
P=B/'stage217-restricted-ET_DYN-boot-module';PREV='f9a6723e6e084f653d482131081c772dbeb7259b0e046535593349b47babea5a'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0';MODULE='6d78dcc3610b229e1b67eb6378af67a071c58ce1686021f6c3be33d7ef6d31af'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):(H/n).open('x').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def volume():
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==71
for x in prior['files']:
 p=R/x['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==x['bytes'] and sha(p)==x['sha256']
sys.path.insert(0,str(H));import dynmodule as D
r=json.loads((H/'runs-final-v2/receipt/results.json').read_text());assert r['status']=='PASS_OWN_PROCESS_FILTER_FIXTURE' and r['tests_run']==11 and r['failures']==r['errors']==0
assert len(r['cases'])==len(r['guests'])==63 and sha(H/'test_process_filter.py')==r['test_source_sha256'] and sha(H/'dynmodule.py')==r['builder_source_sha256']
b=r['build'];assert b['sha256']==MODULE and b['bytes']==262936 and len(b['link_relocations'])==136
assert sha(H/'runs-final-v2/built/boot-module.so')==sha(H/'runs-final-v2/reproducible/boot-module.so')==MODULE
assert sha(H/'boot_module.c')==D.MODULE_SHA==b['module_source_sha256']=='e00334e9e922dd900aad8b0879c8e73baed4ecd1a800c33fa7acdb7ec2f8de98'
fmt=D.inspect((H/'runs-final-v2/built/boot-module.so').read_bytes());assert not fmt['initialization_behavior_verified_by_inspector'] and not fmt['actual_Sony_loader_acceptance_verified']
assert b['fixed_shell_process_filter_implemented'] and not b['exclusive_request_attestation_verified'] and not b['source_initializer_calls_worker_or_syscall']
assert not r['original_Sony_code_executed'] and r['own_ARM64_code_executed'] and not r['real_glibc_Sony_loader_or_Linux_kernel_executed']
assert all(not x['errors'] for x in r['guests'])
assert [x['code'] for x in r['cases'][:2]]==[0,0] and [x['source_reads'] for x in r['cases'][:2]]==[2,2]
for x in r['cases']:
 if not x['name'].startswith(('positive-','worker-')):assert not x['source_opens'] and x['source_reads']==0
assert next(x for x in r['cases'] if x['name']=='before-init')['code']==47
for g in r['guests']:
 assert all(x['number'] not in (93,94) for x in g['syscalls'])
 # Every ordinary fixture called the constructor/status before explicit entry.
 if g is not r['guests'][-1]:assert all(x['syscalls']==0 for x in g['calls'][:3])
derived=json.loads((H/'inner-derivation.json').read_text());original=(R/derived['source']).read_bytes();inner=(H/derived['derived']).read_bytes();at=derived['single_span_offset'];before=derived['before'].encode();after=derived['after'].encode()
assert sha256(original).hexdigest()==derived['source_sha256']==D.B.SOURCE_SHA and sha256(inner).hexdigest()==derived['derived_sha256']
assert original.count(before)==1 and original[at:at+len(before)]==before and inner==original[:at]+after+original[at+len(before):]
proof=json.loads((H/'shell-profile-proof.json').read_text());assert len(proof['original_ranges'])==6 and len(proof['raw_instruction_checks'])==17
assert proof['kernel_cmdline_hex']==r['expected_cmdline_hex'] and proof['kernel_cmdline_bytes']==40 and proof['execv_path']=='/bin/sh'
sources={}
for x in proof['original_ranges']:
 source=R/x['source']
 if source not in sources:sources[source]=source.read_bytes();assert sha256(sources[source]).hexdigest()==x['source_sha256']
 raw=sources[source];data=raw[x['file_offset']:x['file_offset']+x['bytes']];assert data==(H/x['output']).read_bytes() and sha256(data).hexdigest()==x['sha256']
# Re-read both saved official binary byte profiles; they are data, not executions.
p=B/'stage2/extraction/read_filesystems.py';assert sha(p)=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
import importlib.util
sp=importlib.util.spec_from_file_location('readonly218seal',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
exe=json.loads((H/'executable-source-capture.json').read_text())['files'];assert len(exe)==2
for x in exe:
 f=m.Ext2(B/'stage2/extraction'/x['image']);assert sha256(f.b).hexdigest()==x['image_sha256'] and f.data(x['inode'])==(H/x['output']).read_bytes() and sha(H/x['output'])==x['sha256'];f.b.close();f.f.close()
abi=json.loads((H/'ABI-source-capture.json').read_text());raw=(H/abi['output']).read_bytes();assert sha256(raw).hexdigest()==abi['sha256'] and sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()==abi['git_blob_sha1'] and len(abi['lines'])==5
for x in abi['lines']:assert raw.decode().splitlines()[x['line']-1]==x['text']
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert sha(R/release['archive'])==release['archive_sha256']
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
 if '://' not in link and link not in ('verification-receipt.json','final-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-recheck.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('verification-receipt.json',dict(schema='fx3-stage218-shell-process-filter-verification-v1',created_utc=now,status='PASS_11_OWN_PROCESS_FILTER_FIXTURE_TESTS',
 previous_manifest_sha256=PREV,previous_members_reverified=71,module_sha256=MODULE,module_source_sha256=D.MODULE_SHA,
 builder_source_sha256=r['builder_source_sha256'],test_source_sha256=r['test_source_sha256'],
 final_tests_passed=11,fixture_cases=63,raw_original_ranges=6,original_instruction_or_address_checks=17,
 original_first_exec='/bin/sh',exact_cmdline_bytes=40,executable_reference_profiles=2,standard_syscall_lines=5,
 code_link_relocations=136,runtime_initialization_relocations=1,initializer_source_is_memory_only=True,
 accidental_process_filter_implemented=True,unfiltered_inner_entry_dynamic_export=False,entry_before_initialization_denied=True,
 explicit_success_case_chunks=[2,2],real_Sony_code_or_loader_or_Linux_kernel_executed=False,own_ARM64_code_executed=True,
 actual_parent_im_identity_observed=False,exclusive_request_or_launcher_attestation_verified=False,global_claim_implemented=False,
 old_source_release04_and05_and23_source_files_unchanged=True,root01_bundle_and_absent_job_unchanged=True,
 first_invalid_short_read_injection_and_corrected_direct_date_NUL_case_preserved=True,
 all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
 research_activity='Bound original FX3 first exec as /bin/sh,-c,fixed date string via6raw ranges/17word-address checks. Implemented own explicit-entry filter:initialized,main thread/UID/PID,exact40byte procfs cmdline,full reference BusyBox/self and im/parent file hashes/metadata,identity recheck,late/close failure stops and per-instance one-shot. Inner0.5 entry made static by one-span derivation;no unfiltered dynamic export.11final tests/63fake-kernel ARM64 cases pass,2bases each2synthetic blocks. No source auto-dispatch/exit or Sony/Linux/root/device execution;parent profile assumption and request/global claim/completion missing.16requirements,195pending,0.4/0.5 unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-recheck.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active persistent goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('218把原第一层exec绑定为/bin/sh -c固定日期串，6范围/17原字及地址；40字节cmdline、主线程/UID/PID、自身BusyBox和父im后备文件全SHA/元数据及重开检查、时间/close拒绝接入显式入口。原读取入口仅改声明为static无旁路导出，初始化仍纯内存；11最终测试/63夹具、2基址各2合成块通过。真实父进程、内存代码/授权、全局claim和可信完成未证，无Sony/设备/root动作；16要求、195待答及0.4/0.5保留。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/boot_module.c',derivation=REL+'/inner-derivation.json',proof=REL+'/shell-profile-proof.json',builder=REL+'/dynmodule.py',tests=REL+'/runs-final-v2/receipt/results.json',build=REL+'/runs-final-v2/built/build.json',module_sha256=MODULE,scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',own_ARM64_code_executed=True,Sony_or_Linux_execution=False,new_device_operations=0)
new['latest_stage_evidence']['stage218_fixed_first_shell_process_filter']=ev
new['recovery_fixed_shell_process_filter_candidate']={**ev,'source_module_sha256':D.MODULE_SHA,'tests_passed':11,'fixture_cases':63,
 'exact_first_exec':'/bin/sh','exact_cmdline_bytes':40,'reference_self_hash':exe[0]['sha256'],'reference_parent_hash':exe[1]['sha256'],
 'parent_im_profile_is_reference_assumption':True,'actual_body_or_process_memory_attestation_proven':False,
 'accidental_process_filter_implemented':True,'private_inner_worker_has_dynamic_export':False,'constructor_auto_dispatches_or_exits':False,
 'exclusive_request_attestation_or_global_claim_or_trusted_completion_ready':False,
 'actual_Sony_loader_acceptance_or_independent_restore_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
 '195仅主机root01原具体问题待答；不从目标active/继续推导批准，不启动或重问，不扩大相机权限。',
 '218已加第一层shell进程过滤且初始化仍不自动读取；下一项补具体请求与真实启动者/PID/程序绑定、跨进程一次性claim和可信完成回执。进程后备文件SHA及可修改cmdline不能充授权或加载内存认证；先做不访问源分区的离线验证。',
 '真实父im/子BusyBox身份、Sony装载和专用启动/退出尚未实测；原日期副作用、fork失败退出调用者和无超时wait不因新filter消失。不能据进程匹配直接触发旧日期命令或写preload，也不将实例内一次性当全局排他。',
 '保留同机健康boot0/p1/完整配置、独立AP入口、数据视图/访问归还、逆写/冷启动/故障恢复及全部16要求与实际MAIN1080p29.97 HEVC/长录；自建ARM64与假内核通过不充实机备份/恢复或首刷放行。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[k]==old[k],k
for k in old['latest_stage_evidence']:assert new['latest_stage_evidence'][k]==old['latest_stage_evidence'][k]
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3固定shell进程过滤候选](<'+REL+'/README.md>)：首层/bin/sh -c的40字节argv已绑，UID/PID/主线程与自身/父程序文件SHA接入；11项/63夹具通过，无内层旁路导出或自动读取/exit。调用授权、全局claim、真实父进程与完成回执未证；16要求/195待答保留，无设备/root。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
 assert dest.read_bytes()==expected;p=H/name
 with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
 os.replace(p,dest)
members=[]
for p in sorted(H.rglob('*')):
 s=p.lstat()
 if stat.S_ISDIR(s.st_mode):continue
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink();members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage218-first-shell-process-filter-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=71,files=members,member_count=len(members),
 goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
 tests_passed=11,fixture_cases=63,raw_original_ranges=6,original_word_or_address_checks=17,module_sha256=MODULE,
 actual_parent_or_request_authority_proven=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,new_approval_granted=False,
 native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=sha(H/'final-receipt.json'),members=len(members),new_tests=11,fixture_cases=63,module_sha256=MODULE,requirements_unchanged=16,native_goal_status='active',new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
