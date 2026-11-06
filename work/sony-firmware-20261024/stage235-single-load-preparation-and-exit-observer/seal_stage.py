"""Seal useful integration and a remaining FALSE-COMPLETE counterexample.
Passing scoped cases never overrides the explicit failed admission result.
"""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,importlib.util,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage234-fixed-RAM-plan-preparer';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def load(p):return json.loads(p.read_text())
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='76d6babd27647379a883a7bb6af3e24f4451c1cd65560d3294c5262381aaa5c3'
pm=load(P/'final-receipt.json');assert len(pm['files'])==76
for x in pm['files']:
 p=R/x['path'];assert not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
run=H/'runs-integrated-verified';test=load(run/'receipt.json');repro=load(H/'reproducible-build-summary.json');assert test['status']==repro['status']=='PASS' and test['tests']==8 and len(test['cases'])==24 and test['failures']==test['errors']==0
for n,digest in test['source_hashes'].items():assert sha(H/n)==sha(run/'source-snapshot'/n)==digest==repro['source_hashes'][n]
binary=run/'built/parent-module.so';assert sha(binary)==sha(H/'reproducible-build/parent-module.so')==repro['sha256']==test['build']['sha256']=='96816df9bfbb816c0df312ae7281c5483e62142ea8227dbcfe4c63933e5a2e95' and binary.stat().st_size==131864
sp=importlib.util.spec_from_file_location('single235_seal',H/'combined_build.py');d=importlib.util.module_from_spec(sp);sp.loader.exec_module(d);inspection=d.inspect(binary.read_bytes());assert not inspection['has_DT_NEEDED_or_imports'] and inspection['single_constructor_own_NOOP_child_only'] and not inspection['boot_source_USB_or_firmware_backend']
for segment in inspection['segments']:assert not (segment['flags']&1 and segment['flags']&2)
cases={x['name']:x for x in test['cases']};assert len(cases)==24
for row in cases.values():assert not row['summary']['source_accesses'] and not row['summary']['exec_attempts']
for tid in [777,778,779,780]:
 c=cases['normal-'+str(tid)];assert c['result']==[3,0] and c['summary']['own_child_exit']==0 and not c['summary']['remaining_new_FDs'] and c['summary']['final_parent_mask']==0x400 and all(w['role']=='own' and w['mask']&(1<<9) for w in c['summary']['wait_subjects'])
for name in ['post-publish-root-close','expire-after-publish','expire-during-final-close']:assert cases[name]['result'][0]==2 and not cases[name]['summary']['worker_started'] and not cases[name]['summary']['clones']
assert cases['same-creator-after-nonzero']['result']==[2,64] and cases['same-creator-after-nonzero']['summary']['own_child_exit']==68
assert cases['mutate-plan-between']['result']==[4,0] and not cases['mutate-plan-between']['summary']['clones']
assert cases['socket-profile']['result']==[2,43] and not cases['socket-profile']['summary']['remaining_new_FDs']
old=load(H/'old-creator-gap-counterexample.json');assert old['status']=='COUNTEREXAMPLE_REPRODUCED' and len(old['cases'])==3 and old['script_sha256']==sha(H/'check_old_creator_gap.py') and sha(R/old['old_binary_path'])==old['old_binary_sha256'] and old['cases'][-1]['old_result']==[3,0] and old['cases'][-1]['original_child_exit']==68
old=load(H/'plan-substitution-before-fix.json');assert old['old_result']==[3,0] and old['same_inode_plan_nonce_changed_and_CRC_repaired'] and sha(H/old['old_binary_path'])==old['old_binary_sha256'] and sha(H/'plan-substitution-model.py')==old['model_sha256']
residual=load(H/'remaining-parent-identity-counterexample.json');assert residual['status']=='CURRENT_COUNTEREXAMPLE_REPRODUCED_DO_NOT_RELEASE' and residual['current_false_complete'] and residual['must_not_release_this_candidate'] and residual['result']==[3,0] and residual['original_own_child_exit']==68 and residual['reused_PID_foreign_exit']==0
assert residual['current_binary_sha256']==sha(binary) and residual['model_sha256']==sha(H/'model_combined.py') and residual['script_sha256']==sha(H/'check_remaining_parent_identity.py') and residual['creator_signal_mask_still_blocked'] and not residual['current_camera_context_supporting_this_interleaving_measured'] and residual['new_device_operations']==0
assert repro['remaining_parent_sharing_counterexample'] and not repro['probe_deployable'] and not test['first_flash_released'] and test['new_device_operations']==0 and test['boot_device_card_or_recording_source_reads']==0 and test['only_own_ARM64_executed'] and not test['actual_Linux_processes_or_threads_created'] and not test['original_Sony_Linux_or_glibc_executed']
contract=load(H/'kernel-identity-review.json');assert contract['source_only'] and not contract['same_live_creator_inode_is_complete_child_identity_proof'] and contract['parent_sharing_or_adoption_context_unverified'] and not contract['mm_release_notification_is_all_FDs_closed_or_final_reap']
for row in contract['source_ranges']:
 p=R/row['path'];piece=''.join(p.read_text().splitlines(keepends=True)[row['first_line']-1:row['last_line']]);assert sha(p)==row['sha256'] and sha256(piece.encode()).hexdigest()==row['range_sha256'] and all(t in piece for t in row['required_tokens'])
revision=load(H/'source-revisions.json');assert revision['current_C_sha256']==sha(H/'combined.c') and revision['initial_C_sha256']==sha(H/'runs-initial/source-snapshot/combined.c') and revision['seed_generator_recreates_initial_source_only']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();prior=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(prior['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='INTEGRATED_LOCAL_FLOW_PASS_BUT_CURRENT_PARENT_IDENTITY_COUNTEREXAMPLE_ADMISSION_FAILED',scoped_tests=8,scoped_model_cases=24,remaining_admission_counterexamples=1,own_ELF_bytes=131864,own_ELF_sha256=sha(binary),single_constructor_preparation_success_to_launch_gate_implemented=True,complete_prepared_plan_hash_bound_across_activation=True,continuous_creator_signal_mask_through_collection_implemented=True,current_false_complete_under_parent_sharing_or_adoption_model=True,complete_child_identity_proof=False,actual_parent_context_or_request_timing_verified=False,probe_deployable=False,full_boot_worker_integrated=False,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:234 own complete RAM-plan preparation and source-model handoff sealed',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=76,source_hashes=test['source_hashes'],scoped_test_receipt='runs-integrated-verified/receipt.json',failed_admission_receipt='remaining-parent-identity-counterexample.json',positive_tests_cannot_override_remaining_false_complete=True,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Single-load own NOOP component integrates234 preparation completion directly into launch, exact full-plan SHA binds same-inode data, continuous creator mask covers clone through bounded privateDONE/wait.8scoped checks/24cases and reproducible131864B ELF. Old231same-live-creator gap false-complete and initial merged plan substitution reproduced; ordinary signal/callback gap and substitution fixed. HOWEVER current binary still falsely accepts parent-sharing/adopted eligible replacement after externalWALL model reaping: own exit68 mistaken for foreign0 while mask blocked. Explicit residual counterexample pins current binary; safety admissionFAILED, no deployment. Reference fork/exit permits parent sharing/reparenting; actual parent domain unmeasured. Next investigate job-bound kernel exit evidence independent of recycled numericPID; early mm_release markers not finalFD/exit proof. No device/root operations; full16requirements/formal sources unchanged.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('235合并准备成功到启动及同次观察，自写8检查/24范围内场景和131864B重复构建一致；修复同inode改计划仍启动和临时socket失败泄漏，普通信号回调间隙以连续屏蔽收拢。另复现旧231同活创建者PID误认，并确认当前合并二进制在父共享/线程收养条件模型中仍把原exit68当新exit0，安全准入明确失败，不能投放。固定kernel父关系/退出顺序，下一步找任务唯一内核退出凭据，mm_release早于exit_files不充最终资源归还。16/195/正式包保留，无设备/root。')
ev=dict(readme=rel+'/README.md',source=rel+'/combined.c',builder=rel+'/combined_build.py',model=rel+'/model_combined.py',scoped_receipt=rel+'/runs-integrated-verified/receipt.json',failed_admission=rel+'/remaining-parent-identity-counterexample.json',old_creator_gap=rel+'/old-creator-gap-counterexample.json',kernel_contract=rel+'/kernel-identity-review.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage235_single_load_and_remaining_identity_counterexample']=ev;new['recovery_single_load_preparation_and_exit_observer']=ev
new['corrections_to_prior_stage']['stage231_same_creator_guard_scope']=dict(old_other_thread_replacement_rejection_preserved=True,same_live_creator_inode_does_not_pin_child_PID_across_loads=True,current_single_call_mask_removes_only_signal_callback_gap=True,complete_child_identity_proof=False,source=rel+'/old-creator-gap-counterexample.json',remaining_current_counterexample=rel+'/remaining-parent-identity-counterexample.json',first_flash_released=False)
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['优先解决235当前反例：数字PID+活创建线程+WNOTHREAD仍可能混入父共享/收养子进程，当前安全准入失败；不把8检查/24范围内通过充完整身份验收，不投放该程序。','研究与本次任务唯一对象绑定、不依赖复用PID的内核退出凭据。核对robust-futex清理/clear_child_tid/源码顺序及实际可用条件；mm_release早于exit_files，不能把早期标记充全部FD归还或最终退出码，当前未实现。','保留准备完成到启动的同调用门和完整计划SHA、不覆盖发布、连续掩码及超时HELD；核对服务请求时限与主机独立回传，未验证内核/父域/加载/真实机身身份，不能通过放宽条件制造可上机结论。','入口及身份合同解决后整合完整boot采集、同机健康备份、独立AP救砖逆写冷启动和MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16要求。195root01未批准不启动，正式0.4/0.5不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert prior[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3单次加载集成与剩余身份反例](<'+rel+'/README.md>)：准备到启动/观察已合并，8检查24范围内场景及重复构建通过；完整计划SHA与连续掩码修复两处缺口。但当前父共享/收养模型仍误认exit68为0，安全准入失败，继续研究唯一内核退出凭据；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage235-integration-with-failed-child-identity-admission-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
