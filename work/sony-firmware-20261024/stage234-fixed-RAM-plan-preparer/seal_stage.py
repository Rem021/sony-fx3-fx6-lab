"""Seal own synthetic RAM-plan component; no target execution is released."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,importlib.util,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage233-kernel-UIPC-callback-slot-assignment';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def load(p):return json.loads(p.read_text())
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='165a3ba9f7f8ae7fc1ad2a407f2bb6e720e92b42c5ecf50062eb334ef004fbd4'
pm=load(P/'final-receipt.json');assert len(pm['files'])==15
for x in pm['files']:
 p=R/x['path'];assert not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
run=H/'runs-final-close-checked';receipt=load(run/'receipt.json');repro=load(H/'reproducible-final-summary.json');assert receipt['status']==repro['status']=='PASS' and receipt['tests']==7 and len(receipt['cases'])==27 and receipt['failures']==receipt['errors']==0
assert receipt['only_own_ARM64_executed'] and not receipt['actual_Linux_processes_or_threads_created'] and not receipt['original_Sony_Linux_or_glibc_executed'] and receipt['new_device_operations']==receipt['boot_device_card_or_recording_source_reads']==0
for n,digest in receipt['source_hashes'].items():assert sha(H/n)==sha(run/'source-snapshot'/n)==digest==repro['source_hashes'][n]
binary=run/'built/parent-module.so';assert sha(binary)==sha(H/'reproducible-final/parent-module.so')==repro['sha256']==receipt['build']['sha256']=='48dd484aeb42af4465e237ecf97fec4e467639e4ed5d15dc890491fa066994a3' and binary.stat().st_size==131864
s=importlib.util.spec_from_file_location('prepare234_seal',H/'prepare_build.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d);inspection=d.inspect(binary.read_bytes());assert inspection['normalized_image_sha256']==repro['normalized_sha256'] and not inspection['has_DT_NEEDED_or_imports'] and not inspection['child_identity_guard_implemented'] and inspection['no_child_lifecycle_in_this_component']
assert not inspection['normalized_self_consistency_is_authentication_or_live_body_attestation'] and inspection['fixed_synthetic_associations_only'] and inspection['expected_worker_sha256']=='c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec'
for segment in inspection['segments']:assert not (segment['flags']&1 and segment['flags']&2)
assert not receipt['actual_tmpfs_renameat2_loader_body_or_host_transport_verified'] and not receipt['START_to_OBSERVE_transition_implemented'] and not receipt['full_boot_worker_integrated'] and not receipt['first_flash_released']
cases={x['name']:x for x in receipt['cases']};assert len(cases)==27
for row in cases.values():assert not row['summary']['forbidden_syscalls']
normal=cases['normal'];assert normal['result']==[1,0] and not normal['summary']['remaining_new_FDs'] and len(normal['summary']['publications'])==1 and normal['summary']['publications'][0]['published']
for name in ['expire-after-publish','expire-during-final-close']:assert cases[name]['result']==[2,21] and cases[name]['summary']['publications'][-1]['published']
for name in ['existing-plan','publish-race','rename-unsupported']:assert cases[name]['result']==[2,17] and not cases[name]['summary']['publications'][-1]['published']
assert cases['post-publish-root-close']['result']==[2,20] and cases['post-publish-root-close']['summary']['remaining_new_FDs']
assert cases['worker-start-handoff']['result']==[1,0] and cases['replay']['result']==[2,11]
for name,source,flag in [('post-publication-expiry-before-fix.json','expiry-counterexample-model.py','old_false_ready_after_publication_expired'),('cleanup-expiry-before-fix.json','cleanup-expiry-counterexample-model.py','old_false_ready_after_final_close_expired')]:
 c=load(H/name);assert c[flag] and c['old_result']==[1,0] and c['modeled_target_clock']>=c['generated_plan_deadline'] and c['actual_device_operations']==0 and sha(H/c['old_binary_path'])==c['old_binary_sha256'] and sha(H/source)==c['model_sha256']
for row in load(H/'kernel-source-capture.json'):assert row['returncode']==0 and (H/row['path']).stat().st_size==row['bytes'] and sha(H/row['path'])==row['sha256']
contract=load(H/'kernel-contract-review.json');assert contract['source_only'] and contract['syscall']==276 and contract['flags']==1 and not contract['actual_target_renameat2_tmpfs_or_privileges_verified']
for row in contract['source_ranges']:
 p=R/row['path'];piece=''.join(p.read_text().splitlines(keepends=True)[row['first_line']-1:row['last_line']]);assert sha(p)==row['sha256'] and sha256(piece.encode()).hexdigest()==row['range_sha256'] and all(t in piece for t in row['required_tokens'])
assert sha(B/'stage231-constructor-noexec-child-and-reload-observer/runs-bounded-verified/built/parent-module.so')==inspection['expected_worker_sha256']
assert sha(B/'stage231-constructor-noexec-child-and-reload-observer/model_entry.py')=='c1787e53acdc812ef9202007d03b6a4b0bf9e58b8ec8e720e36f26f01583f48a'
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='OWN_FIXED_RAM_PLAN_PREPARER_MODEL_PASS_NOT_DEPLOYABLE',tests=7,model_cases=27,own_ELF_bytes=131864,own_ELF_sha256=sha(binary),private_staging_full_readback_and_no_replace_publication_implemented=True,final_success_after_directory_close_and_clock_recheck=True,generated_plan_to_existing_own_worker_START_modeled=True,normalized_self_check_is_authentication=False,synthetic_associations_only=True,START_to_OBSERVE_transition_implemented=False,preparer_completion_to_worker_activation_gate_integrated=False,full_boot_worker_integrated=False,real_kernel_loader_rename_tmpfs_body_or_host_transport_verified=False,probe_deployable=False,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:233 kernel receive assignment and16 conditional schedules sealed',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=15,source_hashes=receipt['source_hashes'],current_test_receipt='runs-final-close-checked/receipt.json',reproducible_build='reproducible-final-summary.json',two_old_own_binary_false_ready_counterexamples_preserved=True,**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Own fixed synthetic RAM-plan preparation constructor implemented:7checks/27fake-kernel cases, reproducible131864B ELF. Embeds fixed workerSHA/nonce/associations, samples target monotonic clock, creates0700one-shot RAM staging, O_RDWR EXCL NOFOLLOW0600full plan/readback and STAGED receipt. renameat2 NOREPLACE only, preserves existing/racing targets; post-publish inode/content/FD failures stayHELD. Old own binaries falsely ready when publish/finalclose crosses deadline reproduced; success now after directory closure and final clock check. Generated plan accepted by unchanged231own worker START and NOOPchild exits0 in model. Self-normalized SHA is consistency not authentication, associations artificial; plan existence not activation permission. Transition/completion gate/host readback/thread timing/fullboot/independent recovery remain unintegrated. No device/root operations;16requirements/formal sources unchanged.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('234实现完整RAM计划准备候选，7检查/27模型场景及131864B重复构建一致：固定workerSHA/人工关联、自采单调时钟、私有0700/0600暂存复读、renameat2不覆盖发布和同inode复核；正常生成计划被原231自写START接受，空操作child退出0。复现发布/最终关闭过期仍成功的两个旧程序反例，成功改在目录关闭后复核时钟。发布后失败仍HELD且留记录，不将STAGED/文件存在作启动许可；自规范化SHA不充认证，转换/准备完成准入/主机回传/线程时限/完整备份恢复仍缺。16/195/正式包不变，无设备/root。')
ev=dict(readme=rel+'/README.md',source=rel+'/prepare.c',builder=rel+'/prepare_build.py',model=rel+'/model_prepare.py',tests=rel+'/test_prepare.py',receipt=rel+'/runs-final-close-checked/receipt.json',reproducible=rel+'/reproducible-final-summary.json',kernel_contract=rel+'/kernel-contract-review.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage234_fixed_RAM_plan_preparer']=ev;new['recovery_fixed_RAM_plan_preparer']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['补固定准备程序完成到工作启动的独立准入：已发布计划/STAGED文件不能证明准备完成，发布后失败可能留完整计划；不得自动删除/重试或只看文件存在。当前人工关联和自校验不能充真实身份/授权。','实现并验证计划START到OBSERVE转换及主机结果回传，固定模式/nonce/SHA/期限/原对象关系；不要把模型中人为改计划充实际协议。','优先核对同次构造加载内有界任务和独立退出观察的请求时限/同步返回/停止超时，保留233多接收槽事实及231活线程/proc锚/WNOTHREAD；跨线程替代另证PID复用安全。','入口合同解决后整合完整boot采集、同机健康备份及独立AP救砖逆写冷启动；MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16要求保持，195root01未批准不启动，正式0.4/0.5不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3完整RAM计划准备程序候选](<'+rel+'/README.md>)：7检查/27模拟场景及重复构建通过，私有0600完整计划复读、不覆盖发布、自采时钟，接原231自写START；修复发布/最终关闭过期误报。人工关联与自校验不充认证，准备完成准入/转换/回传/备份恢复未验，无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage234-own-RAM-plan-preparer-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
