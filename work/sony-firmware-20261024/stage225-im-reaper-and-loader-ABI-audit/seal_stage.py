"""Seal static current-im evidence and own ARM64 reaper counterexample."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage224-controlled-launcher-and-preexec-image-pin';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='721ecef4277394bff10915c78eb4296714bbf206ab202bab6d4efce1b0daafff';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0';PARENT='c3e1d45b55fb8c4c228e7fe4b78cbe702ef81fcd2406f882fe374310198c93dd'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==870
for row in prior['files']:
 p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
a=json.loads((H/'im-loader-and-reaper-audit.json').read_text());im=R/a['source']['path'];assert sha(im)==a['source']['sha256']=='5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91' and im.stat().st_size==40920
assert sha(R/a['source_capture_record'])==a['source_capture_sha256']
assert a['SIGCHLD_handler']==0x402f4c and a['SIGCHLD_number']==17 and a['handler_waitpid_pid']==-1 and a['handler_waitpid_options']==1 and a['handler_loops_while_return_positive']
assert a['all_BL_shaped_text_words_targeting_waitpid']==[0x402f60] and len(a['slices'])==6 and len(a['manual_encoding_and_PLT_checks'])==8
for row in a['slices']:
 raw=bytes.fromhex(row['original_hex']);assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'] and len(row['instructions'])*4==len(raw)
assert a['CLONE_zero_plus_WCLONE_not_a_fix'] and not a['clone_signal_zero_survives_exec'] and not a['native_loader_establishes_own_four_argument_submit_contract']
for row in a['kernel_reference_ranges']:
 p=R/row['path'];assert sha(p)==row['source_sha256'];lines=p.read_text().splitlines(keepends=True);piece=''.join(lines[row['first_line']-1:row['last_line']]);assert sha256(piece.encode()).hexdigest()==row['range_sha256'] and all(t in piece for t in row['required_tokens'])
assert 'list_for_each_entry(p, &tsk->children, sibling)' in (H/'source-reference/exit.c').read_text()
for cap in json.loads((H/'kernel-source-capture.json').read_text())['sources']:assert cap['returncode']==0 and (H/cap['path']).stat().st_size==cap['bytes'] and sha(H/cap['path'])==cap['sha256']
r=json.loads((H/'probe-first/receipt/reaper-probe.json').read_text());assert len(r['records'])==r['new_own_ARM64_schedules']==2 and r['all_fixture_threads_terminal'] and r['own_parent_child_ARM64_executed'] and not r['Sony_im_handler_or_Linux_kernel_executed']
assert r['probe_source_sha256']==sha(H/'probe_reaper.py')
for p,digest in r['reused_helpers'].items():assert sha(R/p)==digest
base,race=r['records'];assert base['name']=='baseline' and race['name']=='reaper-race'
assert base['state']==0 and race['state']==2 and not base['model_reaper'] and len(race['model_reaper'])==1 and -10 in race['own_wait_returns']
for c in r['records']:
 assert c['parent_module_sha256']==PARENT and c['child_return']==c['raw_exit_status']==0 and c['child_packets']==[2,4] and c['source_reads']==2 and not c['parent_errors'] and not c['child_errors']
 assert len(c['clones'])==1 and c['clones'][0]['flags']==17
assert race['same_owner_relaunch_denied_without_new_activity'] and race['new_owner_cannot_reclaim']
assert sha(H/'probe-first/built/parent-module.so')==sha(P/'runs-final/built/parent-module.so')==PARENT
failed=json.loads((H/'audit-im-first-failure.json').read_text());assert sha(H/'audit-im-first.py')==failed['initial_script_sha256'] and failed['decoded_instruction_count']==436 and failed['last_whole_text_decoded_pc']==0x402b5c and not failed['waitpid_site_reached']
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
 if '://' not in link and link not in ('implementation-review.json','verification-receipt.json','final-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and old['latest_stage']==P.name and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
scope=dict(scope='reference official7.02 im ELF and Linux4.9 source as static data; own224 ARM64 under two explicitly modeled wait schedules',
 reference_im_main_SIGCHLD_setup_and_any_child_WNOHANG_reaper_bound=True,reference_im_runtime_handler_installed_or_race_frequency_observed=False,
 same_own224_binary_baseline_success_and_reaper_ECHILD_held_counterexample=True,unsafe_release_found=False,direct_im_owner_availability_proven=False,
 native_loader_four_arg_submit_ABI_or_arbitrary_USB_path_proven=False,isolated_keeper_or_loader_bridge_implemented=False,
 zero_signal_clone_then_exec_WCLONE_repair_supported=False,reference_kernel_exec_resets_exit_signal_bound=True,
 original_Sony_handler_Linux_kernel_or_glibc_executed=False,own_parent_child_ARM64_executed=True,own_new_schedules=2,original_static_slices=6,independent_call_PLT_checks=8,
 all_model_threads_terminal=True,first_incomplete_disassembly_assumption_preserved_and_corrected=True,formal23_sources_release04_05_and224_candidate_unchanged=True,
 all16_requirements_and_authorizations_unchanged=True,root195_pending_not_started=True,new_camera_USB_cached_query_root_auth_upload_execution_or_persistent_writes=0,
 previous_goal_turn_classification='progress:224 controlled launch chain implemented and20 model cases passed',meaningful_safe_offline_work_remains=True,same_blocker_no_progress_count=0,
 native_goal_status='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False)
verification=dict(schema='fx3-stage225-im-reaper-loader-ABI-verification-v1',created_utc=now,status='REFERENCE_CONFLICT_AND_OWN_ARM64_COUNTEREXAMPLE_CONFIRMED_NO_TARGET_LAUNCH',previous_manifest_sha256=PREV,previous_members_reverified=870,original_im_sha256=a['source']['sha256'],original_slices=6,independent_PLT_calls=8,kernel_reference_ranges=3,new_own_ARM64_schedules=2,baseline_state=0,reaper_schedule_state=2,child_return0_in_both=True,exact_parent_binary_sha256_unchanged=PARENT,own_ECHILD_guard_and_no_relaunch_preserved=True,all_model_threads_terminal=True,zero_signal_clone_exec_WCLONE_shortcut_rejected=True,loader_ABI_bridge_and_isolated_keeper_still_missing=True,actual_runtime_handler_or_camera_backup_restore_proven=False,formal23_sources_release04_05_root01_and224_unchanged=True,all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
 research_activity='Bound reference official7.02 im main signal17 setup at4024d8 to handler402f4c, waitpid(-1,status,1) at402f60 and positive-return loop. Six byte slices/eight independent branch+PLT checks; full aligned BL-word scan corrected incomplete Capstone text iteration. Same224parent binary own ARM64 baseline0 vs explicit im-reaper-wins schedule2/ECHILD while childDONE0/exit0/source2; no relaunch or owner reclaim. Linux4.9 eligible_child/WCLONE and exec de_thread unconditional SIGCHLD reset rule reject clone0+WCLONE shortcut. Native im dlopen/dlsym call sites do not construct own submit4arg contract. Direct im ownership availability remains unproven; next own isolated keeper and explicit loader ABI bridge require new parent-image/task binding, not guard deletion. Sony/kernel not executed, no device/root,16requirements/195pending/formalpackages and224candidate unchanged; goalactive not complete.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active full goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']='progress:224 controlled launcher8checks20scenarios';new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('225参考7.02 im的SIGCHLD=17注册、waitpid(-1,WNOHANG)循环已由6原切片/8独立BL与PLT核对；同一224父端二进制在原厂回收器抢先的明确模型时序里，子端DONE0/exit0仍得ECHILD并保持UNKNOWN，原/新所有者均不得重启接替。Linux4.9 exec无条件重置SIGCHLD，排除clone0+WCLONE捷径；原厂加载器未构造四参数submit合同。改下一项为独立看护进程及显式加载ABI桥接，并同步版本化父镜像/固定任务绑定，不能删除旧身份检查。首版反汇编停止导致完整性假设失败已保留纠正；未执行Sony/内核/设备/root，16要求/195/正式包和224候选不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',audit=REL+'/im-loader-and-reaper-audit.json',probe=REL+'/probe-first/receipt/reaper-probe.json',probe_source=REL+'/probe_reaper.py',kernel_sources=REL+'/kernel-source-capture.json',scope=REL+'/implementation-review.json',original_slices=6,independent_PLT_calls=8,new_own_ARM64_schedules=2,exact224_binary_unchanged=PARENT,reference_reaper_waitpid_any_child=True,model_ECHILD_hold_counterexample=True,native_loader_four_argument_ABI_bridge_implemented=False,isolated_keeper_implemented=False,actual_target_execution_or_recovery_proven=False,new_device_operations=0)
new['latest_stage_evidence']['stage225_im_reaper_loader_ABI']=ev;new['recovery_im_loader_reaper_compatibility']=ev
new['next_safe_offline_actions']=['195仅主机root01具体批准仍待答；继续/active不充批准，不启动或重问，不扩大相机权限。',
 '225已识别直接im父端与原厂SIGCHLD回收器的退出证明竞争，并复现224候选保持UNKNOWN；下一项实现自写独立看护进程及显式加载ABI适配，先自写代码/假对象。构造函数仅内存，不把dlopen成功或原厂未设四参的间接调用当作可用submit。',
 '若看护进程exec新ELF，223子端固定im父镜像检查会拒绝；同步版本化父镜像/主机固定任务/私有通道绑定，避免删除旧检查、扩大父身份白名单或父子互嵌SHA循环。看护进程只改自己的信号政策，不修改im信号处理，不用clone0+WCLONE规避exec重置信号事实。',
 '继续核对实际加载入口/线程/root域/挂载/孤儿收养及其它waiter；Keeper与worker源读取异常仍UNKNOWN，不凭PID消失/公开文件/超时自动接替。不执行真实认证/上传/加载或相机程序。',
 '保留16要求及MAIN1080p29.97 HEVC/exact30单列/长录；同机健康boot/p1/配置完整备份、真实数据视图与硬件访问归还、独立AP入口、逆写/冷启动仍缺，本轮反例不是首刷放行。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=enc(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3原厂im回收器与加载ABI缺口](<'+REL+'/README.md>)：6原切片/8调用核对及2自写ARM64时序确认，参考im可抢先回收普通子进程，同一224候选在DONE0/exit0后得ECHILD并保持UNKNOWN；exec重置SIGCHLD使clone0捷径无效，四参入口仍需桥接。转向独立看护进程与新身份合同；16要求/195/正式包保留，无设备/root/Sony执行。'
assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
put('implementation-review.json',scope);put('verification-receipt.json',verification);(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
 assert dest.read_bytes()==expected;p=H/name
 with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
 os.replace(p,dest)
members=[]
for p in sorted(H.rglob('*')):
 s=p.lstat()
 if stat.S_ISDIR(s.st_mode):continue
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink();members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage225-im-reaper-loader-audit-seal-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=870,files=members,member_count=len(members),goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,original_slices=6,independent_PLT_calls=8,new_own_ARM64_schedules=2,parent_module_sha256_unchanged=PARENT,reference_conflict_and_model_counterexample_verified=True,actual_camera_runtime_or_recovery_verified=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),original_slices=6,independent_PLT_calls=8,new_own_ARM64_schedules=2,reference_conflict_and_counterexample_verified=True,actual_target_launch_or_recovery_verified=False,requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
