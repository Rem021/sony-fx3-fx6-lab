"""Seal own standalone keeper/worker model artifacts; never device release."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from copy import deepcopy
import ast,json,os,plistlib,re,stat,subprocess,sys,importlib.util
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage225-im-reaper-and-loader-ABI-audit';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='ded6fca7a1f098a9e579d11997622ed2d88fdcc2b6a4fcab4d827aff390d49bf';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
KEEPER='93bcd77751550c7079a38dfe532272ecf71d849f906c4b05d5515267fa888581';WORKER='349115672da2bc494e073472446004ee476c77ecc716756351cfe50a395b66e7'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
previous=json.loads((P/'final-receipt.json').read_text());assert len(previous['files'])==41
for row in previous['files']:
 p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
der=json.loads((H/'source-derivation.json').read_text())
for row in der['references']:assert sha(R/row['path'])==row['sha256'] and (R/row['path']).stat().st_size==row['bytes']
r=json.loads((H/'runs-final/receipt/results.json').read_text());assert r['status']=='PASS' and r['tests_run']==7 and r['failures']==r['errors']==0 and not r['details'] and len(r['cases'])==11 and r['all_model_threads_terminal']
for n,d in r['source_hashes'].items():assert sha(H/n)==d,n
for role,digest in [('keeper',KEEPER),('worker',WORKER)]:
 build=r[role+'_build'];p=H/'runs-final'/(role+'-built')/'worker.elf';assert build['sha256']==sha(p)==sha(H/(role+'-build-first')/'worker.elf')==digest and build['bytes']==262144
 assert not build['runtime_loader_or_imports'] and not build['shared_library_or_constructor_or_Sony_loader_required'] and build['segment_alignment']==65536 and build['ADRP_instruction_page']==4096
 assert build['source_pins']==der['active_source_pins'][role]
 for n,d in build['source_pins'].items():assert sha(H/role/n)==d
 spec=importlib.util.spec_from_file_location('inspect226_'+role,H/role/'static_build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert m.SOURCE_PINS==build['source_pins'] and m.read_executable(p.read_bytes())==build['segments']
assert 'parent_module.c' not in r['keeper_build']['source_pins']
kr=(H/'runs-final/keeper-built/worker.elf').read_bytes();wr=(H/'runs-final/worker-built/worker.elf').read_bytes();assert WORKER.encode() in kr and KEEPER.encode() not in wr and bytes.fromhex(KEEPER) not in wr
assert b'5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91' in kr and b'5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91' not in wr
assert b'FX3HANDOFFv2' in kr and b'FX3HANDOFFv2' in wr and b'FX3IPCGATEv2' in kr and b'FX3IPCGATEv2' in wr
assert (H/'worker/inner_boot_reader.c').read_bytes()==(B/'stage223-static-worker-and-scoped-job-descriptors/inner_boot_reader.c').read_bytes()
assert der['worker_inner_boot_reader_unchanged_sha256']=='a1459db35501716dc414b45479aaa25c1ddb252ec440bd24258c4db7dbd78683'
cases={c['name']:c for c in r['cases']};assert len(cases)==11
assert all(c['keeper_last_syscall']==93 and c['im_action_unchanged'] and all(o['pid']==7001 for o in c['signal_ops']) for c in r['cases'])
assert sum(len(c['worker_returns']) for c in r['cases'])==8
for n in ['normal','full']:
 c=cases[n];assert c['code']==0 and c['kernel_exit_cleanup']==[] and all(x==0 for x in c['worker_returns']) and all(x['state']==0 for x in c['host_results']) and c['im_reaper_attempts'] and all(not x['eligible'] and x['worker_ppid']==7001 for x in c['im_reaper_attempts'])
 assert all(len(fds)==4 and len(set(fds))==4 and 71 in fds for fds in c['worker_FDs'])
assert cases['normal']['source_reads']==[2] and cases['full']['source_reads']==[128,128,128,126]
for n in ['signal-error','signal-query']:assert cases[n]['code']==81 and not cases[n]['worker_returns']
for n in ['job-keeper-hash','host-credentials','host-sequence']:assert cases[n]['code']==83 and not cases[n]['worker_returns']
for n in ['worker-parent-data','worker-old-parent']:assert cases[n]['code']==85 and cases[n]['worker_returns']==[44] and cases[n]['source_reads']==[0] and [x['state'] for x in cases[n]['host_results']]==[2]
assert cases['legacy-hand']['code']==85 and not cases['legacy-hand']['worker_returns']
c=cases['finish-close'];assert c['code']==89 and c['worker_returns']==[0] and c['host_results'][-1]['operation']==2 and c['host_results'][-1]['state']==0 and not c['host_results'][-1]['actual_keeper_exit_observed']
assembly=json.loads((H/'runs-final/assembled/complete.json').read_text());assert assembly['bytes']==33423360 and len(assembly['windows'])==4 and assembly['sha256']==sha(H/'runs-final/assembled/source.boot1')=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625' and not assembly['hardware_validated'] and not assembly['same_body_origin_verified']
assert r['own_keeper_and_worker_static_start_to_exit_executed'] and not r['original_Sony_or_Linux_kernel_or_glibc_executed'] and not r['actual_bootstrap_native_loader_upload_credentials_signals_or_recovery_verified'] and r['new_camera_operations']==0 and not r['flashable']
for failed in json.loads((H/'failed-run-bindings.json').read_text()):
 q=json.loads((R/failed['receipt']).read_text());assert q['status']=='FAIL'
 for row in failed['source_bindings']:assert sha(R/row['path'])==row['sha256']
assert not (H/'runs-credentials-fixed/receipt/results.json').exists() and not json.loads((H/'runs-credentials-fixed/receipt-serialization-failure.json').read_text())['receipt_created']
for cap in json.loads((H/'signal-source-capture.json').read_text()):assert cap['returncode']==0 and (H/cap['path']).stat().st_size==cap['bytes'] and sha(H/cap['path'])==cap['sha256']
abi=json.loads((H/'kernel-ABI-review.json').read_text());assert abi['rt_sigaction_number']==134 and abi['SIGCHLD']==17 and abi['SA_NOCLDWAIT']==2 and abi['sigset_bytes']==8 and abi['raw_sigaction_bytes']==32 and abi['handler_flags_restorer_mask_offsets']==[0,8,16,24]
for source in abi['source_checks']:
 p=R/source['path'];assert sha(p)==source['sha256'];lines=p.read_text().splitlines()
 for check in source['checks']:assert check['token'] in lines[check['line']-1]
assert sha(R/abi['unistd_source'])==abi['unistd_sha256']
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
 if '://' not in link and link not in ('implementation-review.json','verification-receipt.json','final-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and old['latest_stage']==P.name and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
scope=dict(scope='two own static AArch64 programs from _start with own C signal/query, private512host control,4FD worker v2, clone/exec and old arbiter on explicit fake Linux; ordinary Mac files only',
 own_standalone_keeper_and_worker_implemented=True,own_process_SIGCHLD_default_and_NOCLDWAIT_clear_verified_in_model=True,im_signal_disposition_changed=False,
 versioned_parent_image_FD_inode_complete_SHA_private_handoff_association_implemented=True,worker_has_legacy_im_parent_fallback=False,
 worker_to_keeper_SHA_dependency_acyclic=True,hashes_credentials_or_known_packet_magic_are_user_approval_or_attestation=False,
 private_host512_task_result_and_sequence_implemented=True,FINISH_packet_is_actual_keeper_exit_proof=False,
 native_im_loader_ABI_bridge_bootstrap_upload_exec_exit_transfer_implemented=False,actual_Linux_signals_parent_child_FDs_credentials_mount_ELF_or_recovery_verified=False,
 own_keeper_and_worker_ARM64_executed=True,Sony_im_glibc_or_Linux_kernel_executed=False,all_model_threads_terminal=True,
 tests_passed=7,scenarios=11,keeper_instances=11,worker_process_models=8,full_synthetic_bytes=33423360,
 first_model_failures_and_unreported6test_run_preserved=True,formal23_sources_and_release04_05_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
 root195_pending_not_started=True,new_camera_USB_cached_query_root_auth_upload_execution_or_persistent_writes=0,
 previous_goal_turn_classification='progress:225 original-im reaper and loader-ABI gap bound and own counterexample reproduced',meaningful_safe_offline_work_remains=True,same_blocker_no_progress_count=0,native_goal_status='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False)
verification=dict(schema='fx3-stage226-static-keeper-worker-v2-model-verification-v1',created_utc=now,status='PASS_OWN_STATIC_KEEPER_WORKER_V2_ON_FAKE_LINUX_NOT_NATIVE_BOOTSTRAP_OR_RECOVERY',previous_manifest_sha256=PREV,previous_members_reverified=41,tests_passed=7,scenarios=11,keeper_instances=11,worker_process_models=8,keeper_sha256=KEEPER,worker_sha256=WORKER,each_static_image_bytes=262144,initial_and_final_binary_builds_identical=True,mutual_embedded_SHA_cycle=False,private_control512_and_IPC320_handoff256_v2=True,own_SIGCHLD_policy_and_old_im_reaper_not_consuming_worker_in_model=True,wrong_parent_contents_and_legacy_identity_rejected_before_source=True,FINISH0_close_failure_exit89_counterexample=True,all_model_threads_terminal=True,full_synthetic_bytes=33423360,full_synthetic_sha256=assembly['sha256'],actual_native_loader_bootstrap_auth_upload_exec_signals_or_recovery_verified=False,formal23_sources_release04_05_root01_unchanged=True,all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
 research_activity='Implemented own standalone static keeper and v2worker, both262144B:own _start/exit93; keeper validates3 inherited roles/reference-im bootstrap parent, resets/queries only its own SIGCHLD DFL and flags, receives512B private root-parent tasks binding both image SHA/sequence.224arbiter/fixed global claims/staging/clone/CRC/output reread retained. Worker4FD v2 validates parent-image RAM/root0500 inode then full parent-file SHA/length from private handoff188/220; no legacy im fallback, no mutually embedded SHA cycle.7checks/11cases,11keeper/8worker models pass,4windows33423360synthetic bytes assembled; active im-reaper model not eligible for grandchildren. Bad host SHA/credentials/sequence,wrong parent contents/legacy identity rejected. FINISH0 followed by close error exits89; packet is not exit proof. Native im loading/ABI bootstrap/real credentials/signals/Linux/USB or recovery unverified;16requirements/195pending/formal0.4/0.5 preserved; no camera/root/Sony execution.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active full goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']='progress:225 im reaper and ABI static/counterexample audit';new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('226实现独立静态看护与v2工作程序：自写_start/退出，私有512B任务/结果绑定两镜像SHA和序号；看护只清理/回查自身SIGCHLD策略，保留224全局会话/输入暂存/完成复读；工作程序四角色FD、父镜像inode及完整SHA绑定v2handoff188/220，无旧im备用父身份且无互嵌SHA循环。7检查/11场景、11看护/8工作模型及四窗口人工源组装通过；旧协议/父文件/镜像内容与主机凭据/序号错误拒绝，FINISH0之后关闭失败退出89反例保留。模型错误和6项已运行但序列化失败记录保留。真实加载适配/启动交接/退出传输/Linux/备份恢复未证；16要求/195/正式包不变，无设备/root/Sony执行。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',keeper_source=REL+'/keeper/keeper.c',worker_source=REL+'/worker/worker.c',parent_image=REL+'/worker/parent_image.inc',control=REL+'/keeper/host_control.inc',protocol=REL+'/protocol.py',manifest=REL+'/artifact-manifest.json',tests=REL+'/runs-final/receipt/results.json',model=REL+'/keeper_model.py',scope=REL+'/implementation-review.json',ABI=REL+'/kernel-ABI-review.json',keeper_sha256=KEEPER,worker_sha256=WORKER,tests_passed=7,scenarios=11,own_standalone_keeper_and_v2_parent_binding_implemented=True,actual_bootstrap_or_native_execution_or_recovery_verified=False,new_device_operations=0)
new['latest_stage_evidence']['stage226_static_keeper_parent_binding']=ev;new['recovery_static_keeper_and_parent_image_contract']=ev
new['next_safe_offline_actions']=['195仅主机root01具体批准仍待答；继续/active不充批准，不启动或重问，不扩大相机权限。',
 '226独立静态看护与四FD/v2父镜像完整SHA合同已在自己的ARM64/假Linux联通；下一项实现显式原厂加载ABI适配及固定程序对/私有任务/继承FD的im→看护启动交接，先自写代码/假调用边界，不执行Sony加载器、认证上传或相机程序。',
 'FINISH仅准备结束，已有消息state0后控制通道关闭错误/实际退出89反例；真实bootstrap必须提供看护PID/完整镜像/退出结果的独立观察与回传，不能凭FINISH、公开文件或PID消失宣布退出0。',
 '继续核对真实Linux信号/父子/FD/挂载/root域、原厂加载线程、孤儿收养/ptrace/其它waiter；工作未知仍保留原占用，不强杀/复位/自动回收，不放宽父身份或将root凭据/哈希当批准。',
 '保留16要求及MAIN1080p29.97 HEVC/exact30单列/长录；同机健康boot/p1/配置完整备份、真实数据视图与硬件访问归还、独立AP入口、逆写/冷启动仍缺，本轮模型程序对不是首刷放行。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=enc(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3静态看护进程与父镜像v2合同](<'+REL+'/README.md>)：7检查/11场景通过，两自写静态程序_start至退出，独立看护自身SIGCHLD政策、512B任务与四FD父镜像SHA绑定；四窗口人工源完整组装，旧im父文件/协议拒绝。FINISH0后关闭失败退出89不充成功；真实加载交接/退出传输/备份恢复未验，16要求/195/正式包保留，无设备/root。'
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
put('final-receipt.json',dict(schema='fx3-stage226-static-keeper-worker-candidate-seal-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=41,files=members,member_count=len(members),goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,tests_passed=7,scenarios=11,keeper_sha256=KEEPER,worker_sha256=WORKER,own_keeper_worker_v2_model_verified=True,actual_native_bootstrap_or_camera_recovery_verified=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=7,scenarios=11,keeper_sha256=KEEPER,worker_sha256=WORKER,actual_target_launch_or_recovery_verified=False,requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
