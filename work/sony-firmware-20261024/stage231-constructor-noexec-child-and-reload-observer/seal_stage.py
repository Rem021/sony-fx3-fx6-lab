"""Seal own constructor/NOOP model; never authorize a device or write."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
import ast,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage230-constructor-child-entry-portability';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def load(p):return json.loads(p.read_text())
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='8583283d71f9e142855ba8b6c506bf6943e950e776e44d257167729d0b58c052'
pm=load(P/'final-receipt.json');assert len(pm['files'])==21
for row in pm['files']:
 p=R/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
run=H/'runs-bounded-verified';receipt=load(run/'receipt.json');repro=load(H/'reproducible-bounded-summary.json');build=load(run/'built/build.json')
assert receipt['status']==repro['status']=='PASS' and receipt['tests_run']==14 and len(receipt['cases'])==22 and receipt['failures']==receipt['errors']==0
assert receipt['own_ARM64_executed'] and not receipt['real_processes_or_threads_created'] and not receipt['original_Sony_or_Linux_code_executed']
assert receipt['new_camera_operations']==receipt['boot_device_card_or_recording_source_reads']==0 and not receipt['full_boot_capture_worker_integrated'] and not receipt['actual_FX3_kernel_loader_credentials_or_recovery_verified']
assert not receipt['goal_complete'] and not receipt['flashable'] and repro['identical_binary']
for n,digest in receipt['source_hashes'].items():assert sha(H/n)==sha(run/'source-snapshot'/n)==digest==repro['source_hashes'][n]
binary=run/'built/parent-module.so';assert sha(binary)==sha(H/'reproducible-bounded/parent-module.so')==repro['sha256']==build['sha256']=='c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec' and binary.stat().st_size==131864
assert not build['has_DT_NEEDED_or_imports'] and len(build['runtime_relocations'])==1
for s in build['segments']:assert not (s['flags']&1 and s['flags']&2)
cases={x['name']:x for x in receipt['cases']};assert len(cases)==22
for row in cases.values():
 assert not row['exec_attempts'] and not row['source_accesses'] and row['borrowed_FDs_unchanged'] and row['rights_all_closed']
 if row['clones']:assert row['original_file_backing_invalidated_before_child_execution'] and len(row['clones'])==1 and row['clones'][0]['flags']==0 and not row['clones'][0]['shared_VM'] and row['protection_changes']
 assert all(not (p['permissions']&2 and p['permissions']&4) for p in row['protection_changes'])
assert cases['normal']['observations']==[3] and cases['normal']['child_exit']==0 and cases['normal']['waits'][0]['options']==0xa0000001
assert cases['PID-reuse-at-wait']['waits'][-1]['returned']==-10 and cases['other-waiter']['waits'][-1]['returned']==-10
assert cases['mask-restore']['child_exit']==70<<8 and not cases['mask-restore']['child_alive'] and cases['mask-restore']['observations']==[2]
assert cases['close-after-DONE']['child_exit']==68<<8 and cases['close-after-DONE']['observations']==[2]
for name in ['anonymous-allocation','anonymous-executable-permission']:assert not cases[name]['clones']
counter=load(H/'PID-reuse-before-fix.json');assert counter['unsafe_original_child_identity_attribution'] and counter['old_observer_return']==[3,0] and sha(H/counter['old_binary_path'])==counter['old_binary_sha256'] and sha(H/'counterexample-model-source.py')==counter['model_sha256']
counter=load(H/'file-backing-before-fix.json');assert counter['old_probe_not_eligible_for_safe_reload'] and not counter['actual_file_or_camera_touched'] and 'FETCH_UNMAPPED' in counter['after_original_DSO_backing_invalidated'] and sha(H/counter['old_binary_path'])==counter['old_binary_sha256'] and sha(H/'file-backing-model-source.py')==counter['model_sha256']
for name in ['kernel-source-capture.json','proc-source-capture.json','cache-source-mirror-capture.json','cache-generic-source-capture.json']:
 rows=load(H/name);rows=rows if isinstance(rows,list) else [rows]
 for row in rows:assert row['returncode']==0 and sha(H/row['path'])==row['sha256'] and (H/row['path']).stat().st_size==row['bytes']
for name in ['kernel-contract-review.json','cache-contract-review.json']:
 contract=load(H/name);assert contract['source_only']
 for row in contract['source_ranges']:
  p=R/row['path'];piece=''.join(p.read_text().splitlines(keepends=True)[row['first_line']-1:row['last_line']]);assert sha(p)==row['sha256'] and sha256(piece.encode()).hexdigest()==row['range_sha256'] and all(t in piece for t in row['required_tokens'])
gaps=load(H/'provisioning-gaps.json');assert not gaps['probe_deployable'] and not gaps['full_capture_worker_integrated'] and not gaps['real_cache_model_or_hardware_test']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R))
scope=dict(status='OWN_NOOP_CONSTRUCTOR_CHILD_AND_RELOAD_OBSERVER_MODEL_PASS_NOT_DEPLOYABLE',tests=14,model_cases=22,own_ELF_bytes=131864,own_ELF_sha256=sha(binary),anonymous_clone_return_and_original_mapping_independence_modeled=True,foreign_clone_PID_reuse_counterexample_fixed_in_reference_model=True,same_live_creator_thread_proc_anchor_and_WNOTHREAD_implemented=True,no_GO_child_wait_bounded_in_own_program=True,independent_DONE_and_exact_exit0_required=True,full_boot_capture_worker_integrated=False,probe_deployable=False,real_Sony_kernel_loader_credentials_cache_or_recovery_verified=False,entry_result_is_full_RAM_cleanup_or_USB_return_receipt=False,original_Sony_glibc_Linux_or_public_camera_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=21,source_hashes=receipt['source_hashes'],current_test_receipt='runs-bounded-verified/receipt.json',reproducible_build='reproducible-bounded-summary.json',two_old_binary_counterexamples_preserved=True,**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Own constructor-only NOOP substrate implemented for230 direct dlopen/dlclose route.14checks/22explicit fake-Linux scenarios execute only own ARM64; reproducible131864B ELF. Parent unloads before child runs; clone returns inside anonymous own-image copy, all child original DSO mappings removed before execution. Preserved old unmapped-fetch and foreign reused-PID false-success counterexamples; fixed with anonymous clone dispatch, live creator proc inode/thread binding, blocked observer signals and WNOTHREAD. Private DONE plus exact exit0/FD closure required; no GO waits bounded; failures remainHELD. Root0600plan staging, target clock, same-thread authenticated reload, actual identity/kernel/cache/loader/transfer, full boot capture/independent recovery remain unverified. Not deployable;16requirements and authorizations/formal sources unchanged; no device/root operations.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress:230 actual direct constructor route and scope correction'
new['progress_audit']['basis'].append('231实现受限构造启动与二次加载观察：14检查/22模拟场景，自写131864B ELF重复构建一致；保存PID复用误接受和旧库映射失效两反例，以活创建线程proc锚/WNOTHREAD/屏蔽信号及匿名副本内clone修复。父模块卸载且子旧映射失效后仍完成；DONE后exit68/外部回收/权限失败均保持未完成，无GO限次退出70。仅空操作、未接入boot备份；root0600计划投放/时钟/同线程认证加载/真实内核缓存及独立恢复仍缺，不能上机或首刷。16要求/195/正式包保持，无设备/root。')
ev=dict(readme=rel+'/README.md',source=rel+'/entry.c',model=rel+'/model_entry.py',tests=rel+'/test_entry.py',receipt=rel+'/runs-bounded-verified/receipt.json',reproducible=rel+'/reproducible-bounded-summary.json',kernel_contract=rel+'/kernel-contract-review.json',cache_contract=rel+'/cache-contract-review.json',provisioning_gaps=rel+'/provisioning-gaps.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage231_constructor_child_and_observer']=ev;new['recovery_constructor_child_and_reload_observer']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['核对普通服务写入器对RAM计划的权限、路径及时间合同，解决root0600计划安全投放和目标单调时钟获取；不为适配未知写入器放宽权限，不上传。','核对两次直接加载的真实线程/认证会话可达性及独立结果回传；现观察需同一活创建线程，不能退回仅数字PID/TID。','在入口合同解决后整合有界完整boot备份工作程序、四窗口和独立完成证明；保留匿名副本与无exec、全局不复用及失败HELD，不将空操作成功当作备份。','实际机身身份/传输/页与ELF/缓存/内核和资源归还、同机健康完整备份、独立AP恢复及逆写冷启动均未验，MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16要求不变。195root01未批准不启动；正式0.4/0.5不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3构造启动与再次加载退出观察候选](<'+rel+'/README.md>)：14检查/22模拟场景及重复构建通过；匿名副本内clone抵御旧库映射失效，活线程proc锚/WNOTHREAD拒绝PID复用，私有DONE与精确退出联合观察，无GO限次退出。仅空操作，计划投放/同线程加载/真实备份恢复未验；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage231-own-constructor-lifecycle-model-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
