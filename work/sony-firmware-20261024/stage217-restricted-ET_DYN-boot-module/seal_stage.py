"""Verify this own-source ET_DYN milestone; keep every device grant closed."""
from pathlib import Path
from hashlib import sha256,sha1
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R));T=R/'outputs/fx3-recovery-adapter'
P=B/'stage216-upstream-bootrom-collection-and-FX3-portability';PREV='3eb3b33b14de4570cede704bb2d6bc0ede6529aeb7af0db1623a0f5beebfc02f'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
MODULE='dcc741e2346fd58ed8f08955244b8c74b10216043c78c4d53d2734f85ccf43eb'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):(H/n).open('x').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def volume():
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==69
for x in prior['files']:
 p=R/x['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==x['bytes'] and sha(p)==x['sha256']
sys.path.insert(0,str(H));import dynmodule as D
r=json.loads((H/'runs-final/receipt/results.json').read_text());assert r['status']=='PASS_OWN_ET_DYN_TEST_LOADER_ONLY' and r['tests_run']==8 and r['failures']==r['errors']==0
assert sha(H/'dynmodule.py')==r['builder_source_sha256'] and sha(H/'test_dynmodule.py')==r['test_source_sha256']
b=r['build'];assert b['sha256']==MODULE and b['bytes']==262936 and len(b['link_relocations'])==100 and len(b['runtime_relocations'])==1
assert sha(H/'runs-final/built/boot-module.so')==sha(H/'runs-final/second/boot-module.so')==sha(H/'build-first/boot-module.so')==MODULE
assert sha(H/'boot_module.c')==D.MODULE_SHA==b['module_source_sha256']=='99d4ec83403f84473d005eda3da56c5287a0cf4d54e1e81d424e101a5d56398c'
assert sha(T/'native/fx3_boot_reader.c')==b['worker_source_sha256']==D.B.SOURCE_SHA
fmt=D.inspect((H/'runs-final/built/boot-module.so').read_bytes());assert not fmt['initialization_behavior_verified_by_inspector'] and not fmt['actual_Sony_loader_acceptance_verified']
assert not b['child_identity_guard_implemented'] and not b['source_initializer_calls_worker_or_syscall']
assert [len(x['source_reads']) for x in r['guests']]==[2,2,0,0,1,2,0] and len(r['guests'])==7
assert all(not g['errors'] for g in r['guests'])
for g in r['guests'][:2]:
 assert all(c['syscalls']==0 and c['source_reads']==0 for c in g['calls'][:3])
 assert g['calls'][0]['result']==0 and g['calls'][2]['result']==0x4658334d4f443031
 assert g['calls'][3]['result']==0 and g['calls'][4]['result']==10
assert r['own_ARM64_code_executed'] and not r['real_glibc_or_Sony_loader_executed'] and not r['real_Linux_kernel_executed']
assert (H/'runs-final/built/boot-module.so').stat().st_mode&0o777==0o600
# The source-only0.5 release and all current source files remain unchanged.
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text())
assert sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
ref=json.loads((H/'source-retry-capture.json').read_text());p=H/ref['output'];raw=p.read_bytes();assert len(raw)==ref['bytes'] and sha256(raw).hexdigest()==ref['sha256'] and sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()==ref['git_blob_sha1']
for x in json.loads((H/'source-capture.json').read_text())['files']:
 if 'sha256' in x:assert sha(H/'reference'/x['name'])==x['sha256']
x=json.loads((H/'source-machine-recapture.json').read_text());assert sha(H/x['output'])==x['sha256']
lines=json.loads((H/'standard-source-lines.json').read_text())['lines'];assert len(lines)==5
for x in lines:assert sha(H/x['path'])==x['sha256'] and (H/x['path']).read_text().splitlines()[x['line']-1]==x['text']
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
 if '://' not in link and link not in ('verification-receipt.json','final-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-recheck.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('verification-receipt.json',dict(schema='fx3-stage217-ET_DYN-source-candidate-verification-v1',created_utc=now,status='PASS_8_OWN_DYNAMIC_MODULE_FIXTURE_TESTS',
 previous_manifest_sha256=PREV,previous_members_reverified=69,module_source_sha256=D.MODULE_SHA,worker_source_sha256=D.B.SOURCE_SHA,
 builder_source_sha256=r['builder_source_sha256'],test_source_sha256=r['test_source_sha256'],linked_ET_DYN_sha256=MODULE,
 bytes=262936,ELF_type='ET_DYN',program_headers=8,sections=11,code_link_relocations=100,runtime_RELATIVE_relocations=1,
 tests_passed=8,first_run7_tests_preserved=True,guest_cases=7,load_address_bases=[0x10000000,0x100000000],
 own_machine_code_executed=True,real_glibc_Sony_loader_or_Linux_kernel_executed=False,
 initializer_syscalls_in_success_cases=0,explicit_worker_success_case_chunks=[2,2],post_relocation_RELRO_CPU_write_denied=True,
 format_inspector_does_not_attest_constructor_behavior=True,exclusive_child_guard_implemented=False,
 actual_camera_loader_acceptance_or_same_body_backup_or_restore_proven=False,
 standard_source_files=3,standard_bound_lines=5,root01_bundle_and_absent_job_unchanged=True,
 old_release04_and05_and23_source_files_unchanged=True,old58_tests_not_repeated_or_recounted=True,
 all16_requirements_and_authorizations_unchanged=True,camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
 research_activity='Built pinned own0.5 boot reader asPIC+ET_DYN with own memory-only init,2explicit exports,noimports,100code links+1RELATIVE init pointer and RELRO.8final tests pass:own test-loader ARM64 at2ASLR bases,2synthetic chunks each,profile/updater/late/close failures,entry replay,CPU readonly guard,metadata/import rejection and anti-behavior-attestation case. No real glibc/Sony loader or kernel,child-identity guard or camera backend.0.5/0.4 and16requirements/195pending unchanged;source-only work milestone,not flash release.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-recheck.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active persistent goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('217将固定0.5读取C按PIC接成最小ET_DYN，构造函数仅写自身内存，2显式导出、100代码字段+1RELATIVE初始化指针，独立RELRO。8项最终检查通过，两个ASLR地址各2块合成读取，失败返回/再入/CPU只读保护等；metadata不能认证初始化行为反例保持false。未运行Sony/glibc/Linux，专用子进程guard与真实装载未证，无设备/root；0.4/0.5/16要求与195待答不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/boot_module.c',builder=REL+'/dynmodule.py',tests=REL+'/runs-final/receipt/results.json',build=REL+'/runs-final/built/build.json',module_sha256=MODULE,scope=REL+'/implementation-review.json',standard_lines=REL+'/standard-source-lines.json',own_ARM64_guest_executed=True,real_Sony_loader_or_kernel_executed=False,camera_USB_or_root_operations=0)
new['latest_stage_evidence']['stage217_restricted_own_ET_DYN_module']=ev
new['recovery_own_dynamic_module_candidate']={**ev,'ELF_type':'ET_DYN','module_source_sha256':D.MODULE_SHA,'tests_passed':8,
 'explicit_exports':list(D.EXPORTS),'initializer_only_own_memory_under_fixed_source_and_test_scope':True,
 'initializer_automatically_dispatches_worker':False,'runtime_relocations':1,'child_identity_guard_implemented':False,
 'actual_Sony_loader_acceptance_or_process_exit_attested':False,'same_body_origin_or_loaded_driver_identity_verified':False,
 'camera_backend_or_persistent_preload_installer':False,'source_only_work_candidate_not_formal_release':True,
 'actual_backup_or_independent_rescue_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
 '195仅主机root01原具体问题待答；不从目标active/继续推导批准，不启动或重问，不扩大相机权限。',
 '217动态模块只在自建装载器通过，不运行Sony加载器；下一项绑定FX3原固定debug子进程的精确argv、程序身份及调用/返回，再实现限定分派。当前初始化不执行读取或exit；不在主im或其它进程做自动工作，不生成preload安装命令。',
 '专用子进程guard、可信owner/root身份/跨进程退出与临时执行通路仍缺实测；格式检查不认证构造行为，旧05授权不可复用。先保留不读取源分区的离线/主机方案与固定范围，不用0.5 ET_EXEC冒充动态模块。',
 '继续同机健康boot0/p1/完整配置与数据视图、访问选择归还、独立AP入口、逆写/冷启动/故障恢复；恢复器显式绑定相对/绝对坐标及完整尾部，保留16要求与实际MAIN1080p29.97 HEVC长录验收。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[k]==old[k],k
for k in old['latest_stage_evidence']:assert new['latest_stage_evidence'][k]==old['latest_stage_evidence'][k]
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3最小动态启动区模块候选](<'+REL+'/README.md>)：固定0.5源码PIC→ET_DYN，内存标记初始化、100代码字段/1相对重定位及RELRO，8项自建装载/ARM64检查通过；Sony装载器与专用子进程guard未验，无上传/preload安装/设备/root，0.5/16要求/195待答保留。'
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
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage217-restricted-own-ET_DYN-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=69,
 files=members,member_count=len(members),goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
 tests_passed=8,own_ARM64_guest_execution=True,real_glibc_or_Sony_loader_or_Linux_kernel_execution=False,module_sha256=MODULE,
 child_identity_guard_implemented=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,new_approval_granted=False,
 native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=sha(H/'final-receipt.json'),members=len(members),new_tests=8,module_sha256=MODULE,requirements_unchanged=16,native_goal_status='active',new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
