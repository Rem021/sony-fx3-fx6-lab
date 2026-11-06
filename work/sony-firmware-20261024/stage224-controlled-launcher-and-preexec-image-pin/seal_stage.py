"""Verify and seal own ARM64 launch candidate; never device execution/release."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from copy import deepcopy
import ast,json,os,plistlib,re,stat,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage223-static-worker-and-scoped-job-descriptors';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='b0fd624e6f26c1a628cb3acc11d00126e29cf1687c371c7d6387785bf0dad4d6';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
IMAGE='e40d068d43123f8f86eba5c46a1428e02e5e16c84df2211174c578d4cd273d7d';PARENT='c3e1d45b55fb8c4c228e7fe4b78cbe702ef81fcd2406f882fe374310198c93dd'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==700
for row in prior['files']:
 p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
sys.path.insert(0,str(H));import dynparent as D
r=json.loads((H/'runs-final/receipt/results.json').read_text());build=r['build'];cases={c['name']:c for c in r['cases']}
assert r['status']=='PASS' and r['tests_run']==8 and r['failures']==r['errors']==0 and not r['details'] and len(cases)==len(r['cases'])==20 and r['all_model_threads_terminal']
for n,d in r['source_hashes'].items():assert sha(H/n)==d,n
assert build['source_pins']==D.SOURCE_PINS==json.loads((H/'source-pins.json').read_text())
for n,d in D.SOURCE_PINS.items():assert sha(H/n)==d
assert build['sha256']==sha(H/'runs-final/built/parent-module.so')==sha(H/'build-first/parent-module.so')==PARENT
assert build['bytes']==262936 and len(build['link_relocations'])==343
fmt=D.inspect((H/'runs-final/built/parent-module.so').read_bytes());assert set(fmt['exports'])=={'fx3_arbiter_submit','fx3_arbiter_poll'} and not fmt['has_DT_NEEDED_or_imports']
assert b'/dev/' not in (H/'runs-final/built/parent-module.so').read_bytes()
assert sha(P/'runs-import-fixed/built/worker.elf')==IMAGE
success=['normal']+['full-'+str(i) for i in range(4)]
for n,c in cases.items():
 assert c['parent_flags_unchanged'] and not c['child_errors'] and not c['parent_errors']
 if n in success:
  assert c['state']==c['child_exit']==0 and c['parent_packets']==[1,3] and c['child_packets']==[2,4] and c['reaped']
  assert set([0,1,2,900]).issubset(c['exec_closed']) and not set(c['role_FDs']).intersection(c['exec_closed'])
  assert c['events'].index('reserve-session')<c['events'].index('open-image')<c['events'].index('clone')<c['events'].index('pwrite:fx3-boot-handoff-v1.bin')<c['events'].index('send:1')
  assert c['execs'][-1]['environment_empty'] and c['clones'][-1]['flags']==17 and c['clones'][-1]['child_stack']==0
 else:assert c['state']==2
for n in ['image-byte','image-writable','image-owner','image-drift','socketpair','clone','existing','second-owner']:
 assert cases[n]['source_reads']==0 and cases[n]['clones']==[] and cases[n]['parent_packets']==[]
for n,code in [('child-flags',90),('bad-dirent',90),('postfork-image-drift',91),('exec',93),('stage-short',57),('stage-sync',57)]:
 assert cases[n]['child_exit']==code and cases[n]['source_reads']==0 and len(cases[n]['clones'])==1 and cases[n]['reaped']
for n in ['stage-short','stage-sync']:assert cases[n]['parent_packets']==[]
assert cases['bad-output']['state']==2 and cases['bad-output']['child_exit']==0 and cases['bad-output']['child_packets']==[2,4] and cases['bad-output']['source_reads']==2
assert [cases['full-'+str(i)]['source_reads'] for i in range(4)]==[128,128,128,126]
assert len([x for x in cases['full-3']['events'] if x.startswith('create-input:')])==2
assembly=json.loads((H/'runs-final/assembled/complete.json').read_text());assert assembly['bytes']==33423360 and len(assembly['windows'])==4 and assembly['sha256']==sha(H/'runs-final/assembled/source.boot1')=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
assert not assembly['hardware_validated'] and not assembly['same_body_origin_verified']
assert r['own_clone_branches_and_exec_transition_modeled'] and not r['actual_Linux_clone_exec_FD_credentials_or_kernel_ELF_acceptance_verified'] and not r['Sony_BusyBox_glibc_or_Linux_kernel_executed'] and r['new_camera_operations']==0 and not r['flashable']
der=json.loads((H/'source-derivation.json').read_text());base=R/der['parent_source'];assert sha(base)==der['parent_source_sha256'];text=base.read_text()
for ch in der['ordered_changes']:assert text.count(ch['before'])==1;text=text.replace(ch['before'],ch['after'])
assert text==(H/'parent_module.c').read_text() and sha(H/'parent_module.c')==der['parent_derived_sha256']
for n,d in der['unchanged_support'].items():assert sha(H/n)==sha(base.parent/n)==d
for failed in der['failed_runs_preserved']:
 d=json.loads((R/failed['receipt']).read_text());assert d['status']=='FAIL'
 for n,row in failed['matching_sources'].items():assert sha(R/row['path'])==row['sha256']==d['source_hashes'][n]
for cap in json.loads((H/'web-source-capture.json').read_text()):assert cap['returncode']==0 and (H/cap['path']).stat().st_size==cap['bytes'] and sha(H/cap['path'])==cap['sha256']
abi=json.loads((H/'kernel-and-link-ABI-review.json').read_text());u=R/abi['unistd_source'];assert sha(u)==abi['unistd_sha256'];lines=u.read_text().splitlines()
for number,line in abi['syscall_number_lines'].items():assert lines[line-1].endswith(' '+number)
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
scope=dict(scope='own ARM64 parent clone zero/positive branches, own child FD enumeration and exec transition, unchanged223static child and parent completion through fake Linux; ordinary Mac fixture files only',
 controlled_C_launcher_full_image_SHA_raw_clone_child_FD_whitelist_exec_and_staging_implemented=True,own_clone_return_point_machine_code_and_static_start_executed=True,
 parent_global_session_precedes_image_staging_and_clone_in_model=True,initial_inputs_O_EXCL_and_only_live_owner_retained_FD_reuse=True,all20_scenarios_have_specific_reached_branch_assertions=True,
 actual_Linux_kernel_clone_exec_FD_credentials_signals_wait4_mount_ELF_or_im_context_verified=False,actual_authenticated_module_upload_load_call_or_result_transfer_implemented=False,
 actual_target_root_global_domain_all_callers_or_backup_restore_proven=False,clone_signal_inheritance_original_parent_handlers_and_other_waiters_verified=False,
 own_parent_and_child_ARM64_executed=True,Sony_BusyBox_glibc_or_Linux_kernel_executed=False,all_model_threads_terminal=True,
 tests_passed=8,scenarios=20,formal23_sources_release04_05_and_root01_bundle_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
 root195_pending_not_started=True,new_camera_USB_cached_query_root_auth_upload_execution_or_persistent_writes=0,
 previous_goal_turn_classification='no_progress:readiness-only response inspected status but changed no implementation; resumed goal now makes progress',
 meaningful_safe_offline_work_remains=True,same_blocker_no_progress_count=0,native_goal_status='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False)
verification=dict(schema='fx3-stage224-controlled-launcher-model-verification-v1',created_utc=now,status='PASS_OWN_ARM64_LAUNCH_CHAIN_IN_FAKE_LINUX_NOT_TARGET_EXEC_OR_RESCUE',previous_manifest_sha256=PREV,previous_members_reverified=700,tests_passed=8,scenarios=20,parent_module_sha256=PARENT,static_child_sha256_unchanged=IMAGE,parent_module_bytes=262936,code_link_relocations=343,initial_and_final_independent_builds_identical=True,all_model_threads_terminal=True,full_synthetic_bytes=33423360,full_synthetic_sha256=assembly['sha256'],image_mismatch_before_clone_child_failure_and_partial_staging_no_source_verified=True,corrupt_output_held_even_DONE0_exit0=True,parent_FD_flags_unchanged_in_model=True,actual_Linux_clone_exec_or_hardware_rescue_verified=False,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_root01_unchanged=True,new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
 research_activity='Implemented controlled own C launcher in parent submit:child0/fd-1 template only; global session before image/inputs; full pinned223static-image SHA/root0500/stable EOF guard; exclusive retained input FDs; SOCK_DGRAM CLOEXEC pair; raw clone220 SIGCHLD17 without VM/FILES/THREAD; own child enumerates FDs and sets only child table flags, execve221 via imageFD with empty env, failure exits93. Parent fills returned childPID/CRC, pwrite/fsync bound inputs before GRANT; old private completion/wait4/output validation retained.8tests/20scenarios pass,4windows33423360synthetic bytes;image corruption before clone,child setup/exec/partial staging fail without source;DONE0exit0 corrupt output held. Own ARM64 clone branches and static entry executed on explicit fake Linux; no actual kernel/process/loader/credentials/signals/im/global domain or camera recovery proof.16requirements/195pending/formal0.4/0.5 unchanged; no device/root. User resumed native active, read only status.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only; user resumed goal',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='User set goal status active; continue full objective',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']='no_progress:readiness-only reply; no implementation changed';new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('224父端新增完整镜像SHA、受控clone/子FD白名单/exec和受全局会话保护的输入暂存，禁旧外部PID/FD注册入口；自己的ARM64在明确假Linux中从clone返回分支到223静态_start及父端完成判定联通。8检查/20场景通过，四窗口人工源完整组装；镜像破坏、子端设置/exec和暂存失败不读源，输出损坏仍UNKNOWN。初始夹具/模型错误及对应源码保留。真实内核/信号/父身份/加载调用传输与同机备份恢复未证；16要求/195/正式包不变，无设备/root。用户恢复原生active，仅观察未改状态。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/parent_module.c',launcher=REL+'/launch_support.inc',builder=REL+'/dynparent.py',model=REL+'/launch_model.py',tests=REL+'/runs-final/receipt/results.json',build=REL+'/runs-final/built/build.json',scope=REL+'/implementation-review.json',ABI=REL+'/kernel-and-link-ABI-review.json',parent_module_sha256=PARENT,static_child_sha256_unchanged=IMAGE,tests_passed=8,scenarios=20,controlled_C_launch_and_preexec_image_pin_implemented=True,actual_Linux_or_camera_exec_inheritance_or_recovery_verified=False,new_device_operations=0)
new['latest_stage_evidence']['stage224_controlled_launcher']=ev;new['recovery_controlled_launcher_and_preexec_image_pin']=ev
new['next_safe_offline_actions']=['195仅主机root01具体批准仍待答；继续/active不充批准，不启动或重问，不扩大相机权限。',
 '224受控启动链已在自写ARM64/假Linux联通；将固定镜像/请求暂存、父端动态加载与显式调用、结果传输接入同一个受控主机任务合同，先仅自写代码和假对象。尚无已实现并获准的真实认证/上传/执行路径。',
 '核对raw clone的信号继承、真实父端SIGCHLD及其它waiter、加载上下文/root域/挂载执行策略与全局调用覆盖；模型FD复制和exec切换不充目标内核行为，不改变挂载/权限或测试相机。',
 '保留16要求及MAIN1080p29.97 HEVC/exact30单列/长录；同机健康boot/p1/配置完整备份、真实数据视图与硬件访问归还、独立AP入口、逆写/冷启动仍缺，当前模型完成不充首刷放行。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=enc(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3受控启动器与完整镜像预核](<'+REL+'/README.md>)：8检查/20场景通过，自写ARM64的clone分支/子FD清理/exec/静态_start与父端完成连通；全局会话先于暂存，镜像或启动失败不读源，四窗口人工源完整组装。真实Linux/加载传输/信号/机内备份恢复未验，16要求/195/正式包保留，无设备/root。'
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
put('final-receipt.json',dict(schema='fx3-stage224-controlled-launcher-candidate-seal-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=700,files=members,member_count=len(members),goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,tests_passed=8,scenarios=20,parent_module_sha256=PARENT,static_child_sha256_unchanged=IMAGE,actual_Linux_launch_or_camera_recovery_verified=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=8,scenarios=20,parent_module_sha256=PARENT,actual_target_launch_or_recovery_verified=False,requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
