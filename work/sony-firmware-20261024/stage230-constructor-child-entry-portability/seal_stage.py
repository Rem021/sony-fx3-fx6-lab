"""Seal static direct-loader evidence and explicitly scope the ABI correction."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage229-Jiritsu-plugin-lifecycle-contract';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='d5417a6d240455bda9e54a6e9597f109058856582a035517be66c81d387b5f3a'
pm=json.loads((P/'final-receipt.json').read_text());assert len(pm['files'])==16
for row in pm['files']:
 p=R/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
a=json.loads((H/'direct-entry-audit.json').read_text());assert len(a['functions'])==3 and len(a['manual_call_checks'])==16
source=R/a['source']['path'];assert sha(source)==a['source']['sha256'] and source.stat().st_size==225200
assert not a['direct_load']['full_script_interface_needed_for_constructor_code'] and a['direct_load']['neither_full_setter_has_direct_dlsym'] and a['distinction']['stage229_lifecycle_audit_remains_correct_for_script_thread']
assert not a['public_source']['public_source_compiled_imported_or_executed'] and not a['original_Sony_glibc_Linux_or_upstream_program_executed'] and not a['first_flash_released']
for name in ['source-capture.json','payload-source-capture.json']:
 for row in json.loads((H/name).read_text()):assert row['returncode']==0 and (H/row['output']).stat().st_size==row['bytes'] and sha(H/row['output'])==row['sha256']
loader=json.loads((H/'loader-source-capture.json').read_text());assert loader['returncode']==0 and sha(H/loader['path'])==loader['sha256']
heads=json.loads((H/'heads.json').read_text());assert len(heads['results'])==2 and all(x['returncode']==0 for x in heads['results'])
assert heads['results'][0]['stdout'].split()[0]==a['public_source']['chocotan_commit'] and heads['results'][1]['stdout'].split()[0]==a['public_source']['FireHydrant_commit']
ref=R/a['kernel_page_reference']['path'];assert sha(ref)==a['kernel_page_reference']['sha256'] and a['kernel_page_reference']['reference_only_not_current_body_kernel_measurement']
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='DIRECT_DLOPEN_CONSTRUCTOR_ROUTE_PINNED_SEPARATE_FROM_SCRIPT_ABI',complete_original_functions=3,manual_call_checks=16,public_repositories_pinned=2,full_script_ABI_is_universal_loader_prerequisite=False,stage229_script_thread_lifecycle_findings_preserved=True,constructor_launch_adapter_or_independent_completion_implemented=False,actual_FX3_loader_or_child_or_recovery_verified=False,original_Sony_glibc_Linux_or_public_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=16,source_sha256=sha(source),**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Pinned actual FX3 direct setter route:3complete functions/16calls, fixed libJit path and dlopen1 then dlclose without dlsym in both setters. Full229script object ABI remains specific to jit_thread, not a universal constructor prerequisite. Public A7CII/FX30 constructor child source pinned; no import/compile/execute. Existing227ctor only marks memory and direct setter never invokes step/status, so not usable as-is. Public SIGCHLD shell child/echo lacks required independent exit proof; reject unverified self-delete/generic shell copy.5MiB FX3 check is cache branch, foreign limits not portable;4KiB GPL reference not live kernel proof. No camera/root operations;16requirements and formal sources preserved.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress:229 actual script ABI and stop completion limits'
new['progress_audit']['basis'].append('230新增直接setter三完整原函数/16调用证明：固定libJit写后dlopen1/成功dlclose、两函数无dlsym；限定229对象ABI仅脚本线程，构造函数路线不要求四导出。固定两公开仓库/载荷及glibc初始化原文，227仅内存构造不激活step；转向受限构造启动器、非共享子进程与独立完成观察。公开通用shell/自删/echo状态不照搬；跨机型上传上限及GPL4K配置不充实机，16要求/195/正式包保持，无设备/root。')
ev=dict(readme=rel+'/README.md',audit=rel+'/direct-entry-audit.json',verification=rel+'/verification-receipt.json',source_capture=rel+'/source-capture.json',payload_source_capture=rel+'/payload-source-capture.json',scope=scope)
new['latest_stage_evidence']['stage230_constructor_direct_entry']=ev;new['recovery_constructor_direct_entry_portability']=ev
new['corrections_to_prior_stage']['stage229_script_ABI_scope']=dict(script_thread_findings_preserved=True,full_script_interface_not_required_by_direct_setters=True,direct_setters_dlopen_then_dlclose_without_dlsym=True,source=rel+'/direct-entry-audit.json',existing227_constructor_still_only_memory_marker=True,device_authorization_expanded=False)
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['优先实现直接dlopen/dlclose所需受限构造启动器及不共享地址空间的自写子进程合同，不必先实现无关的四个脚本接口；构造必须有界并迅速返回，不退出服务、不复制通用shell。','完成父端已卸载后的私有完成和独立退出观察、镜像/任务/身份/全局排他绑定；普通SIGCHLD子退出可能被im回收，公开echo或PID消失不能替代。非SIGCHLD且不exec仅为待证候选，不能忽略exec重置。','区分FX3普通写入与actionff缓存分支容量、实际传输/分配/ELF兼容；先做无源读取的入口候选，尚无获批可执行方案，不上传或调用任何相机接口。','保留16完整要求、MAIN1080p29.97 HEVC42010约16Mbps/exact30单列、音画长录/同机健康完整备份/访问归还/独立AP恢复/逆写冷启动；195root01未具体批准，不启动或重问，正式0.4/0.5不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3直接构造函数入口适配依据](<'+rel+'/README.md>)：3完整原函数/16调用证明两setter写后dlopen/dlclose且无dlsym，229完整对象ABI仅限脚本线程；固定公开A7CII/FX30构造子进程文本，转向受限构造启动器。现227仍只写内存标记，完成/退出/真机恢复未验；无设备/root，不能首刷。'
assert ib.decode().count(marker)==1 and entry not in ib.decode();ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode();after=enc(new)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
for dst,data in [(canonical,after),(index,ia)]:
 tmp=H/('.'+dst.name+'.tmp')
 with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,dst)
members=[]
for p in sorted(H.rglob('*')):
 s=p.lstat()
 if stat.S_ISDIR(s.st_mode):continue
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink();members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage230-direct-constructor-entry-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
