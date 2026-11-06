"""Seal static-interface findings and finite negative models, never admission."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage235-single-load-preparation-and-exit-observer';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def load(p):return json.loads(p.read_text())
def put(n,x):(H/n).open('xb').write(enc(x))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
prev=sha(P/'final-receipt.json');assert prev=='f0318712e77581c69d7f31b77b1cc4f49cb9138ca4986fbc20bbc729869212df'
pm=load(P/'final-receipt.json');assert len(pm['files'])==55
for row in pm['files']:
 p=R/row['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
a=load(H/'kernel-interface-audit.json');assert a['status']=='STATIC_CHECKS_PASS_NOT_RUNTIME_ACCEPTANCE' and a['checks']==len(a['check_names'])==99 and a['catalog_symbols']==41269 and a['native_syscall_count']==291
assert sha(R/a['original_kernel'])==a['original_kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c' and sha(R/a['parser'])==a['parser_sha256']=='db8a1ebba52e8bfb85367e3d8450e1ef89224d0bb9e768bf656c6370600614a1'
assert len(a['syscall_table'])==9 and len(a['source_ranges'])==10 and a['source_reads_only'] and not a['original_kernel_or_Sony_code_executed'] and a['new_device_operations']==0
raw=(R/a['original_kernel']).read_bytes();spans=load(H/'original-selected-spans.json');assert len(spans)==18
for row in spans:
 piece=raw[row['start']:row['end']];assert len(piece)==row['bytes']==4*len(row['instructions']) and sha256(piece).hexdigest()==row['sha256']
 for n,i in enumerate(row['instructions']):assert i['offset']==row['start']+4*n and bytes.fromhex(i['word'])==piece[4*n:4*n+4]
for row in a['source_ranges']:
 p=R/row['path'];piece=''.join(p.read_text().splitlines(keepends=True)[row['first_line']-1:row['last_line']]);assert sha(p)==row['sha256'] and sha256(piece.encode()).hexdigest()==row['range_sha256'] and all(t in piece for t in row['required_tokens'])
captures=load(H/'stable-source-capture.json')+[load(H/'pid-source-capture.json'),load(H/'modern-number-source-capture.json')]
assert len(captures)==7
for row in captures:
 p=H/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and row.get('returncode',0)==0
n=load(H/'modern-number-crosscheck.json');assert n['status']=='PASS' and len(n['rows'])==3 and n['source_sha256']==sha(H/'crosscheck_modern_numbers.py') and n['saved_FX3_audit_sha256']==sha(H/'kernel-interface-audit.json') and all(x['outside_saved_FX3_native_dispatch'] for x in n['rows'])
m=load(H/'wait-reference-model-receipt.json');assert m['model_sha256']==sha(H/'wait_reference_model.py') and m['status']=='MODEL_PROPERTIES_PASS_WITH_EXPLICIT_REMAINING_COUNTEREXAMPLES'
assert (m['ungated_blocking_schedules'],m['ungated_false_complete_count'],m['gated_ordinary_exit_schedules'],m['gated_ordinary_exit_false_complete_count'])==(12,1,3,0)
assert len(m['other_identity_counterexamples'])==4 and len(m['robust_lifecycle_cases'])==3 and len(m['clear_child_tid_cases'])==2 and m['finite_model_claims_only'] and not m['proof_for_arbitrary_kernel_interleavings'] and not m['deployable'] and not m['first_flash_released'] and not m['stage235_candidate_changed_or_admission_failure_cleared']
assert not m['own_candidate_or_original_Linux_executed'] and not m['actual_processes_or_threads_created'] and m['new_device_operations']==0
residual=load(P/'remaining-parent-identity-counterexample.json');assert residual['must_not_release_this_candidate'] and residual['current_false_complete'] and residual['result']==[3,0] and residual['original_own_child_exit']==68
assert sha(P/'runs-integrated-verified/built/parent-module.so')==residual['current_binary_sha256']=='96816df9bfbb816c0df312ae7281c5483e62142ea8227dbcfe4c63933e5a2e95'
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
assert (H/'audit-attempt1.stderr.txt').read_text().endswith('AssertionError: source range pid.c:250\n')
for n in ['audit-attempt2.stderr.txt','wait-model.stderr.txt','modern-number.stderr.txt']:assert (H/n).read_bytes()==b''
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();prior=json.loads(before)
native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(prior['requirements'])==16 and not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='STATIC_EXIT_INTERFACE_AUDIT_AND_FINITE_MODELS_ONLY_IDENTITY_ADMISSION_STILL_FAILED',static_checks=99,original_native_spans=18,source_ranges=10,original_symbols=41269,source_files_captured=7,ungated_schedules=12,ungated_false_complete_count=1,gated_ordinary_exit_schedules=3,additional_identity_counterexamples=4,robust_lifecycle_cases=3,clear_child_tid_cases=2,ordinary_single_wait_object_reference_evidence_bound=True,complete_child_identity_proof=False,isolated_collector_implemented=False,stage235_candidate_unchanged_and_not_deployable=True,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:235 integrated single-load flow and reproduced remaining false-complete admission counterexample',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=55,static_audit='kernel-interface-audit.json',finite_model='wait-reference-model-receipt.json',existing_failed_admission=str((P/'remaining-parent-identity-counterexample.json').relative_to(R)),initial_source_range_error_preserved_and_corrected=True,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Saved official7.02 Image actual native dispatch count291,9syscall entries, wait object reference acquisition/pointer matching/release and earlyfutex exit/exec cleanup bound by99static checks18spans10source ranges.41269symbols reverified. Modern pidfd424/434/438 out of ordinary dispatch; no claim excluding vendorcustom interfaces. Late4.9.337source captured, unlike older4.9 cleanup layout. Finite own model12ungated schedules/1wrong-object0;3normal-gated schedules avoid it but four separate counterexamples retain prelookupSIGKILL, userspace-entering flag and interrupted retry gaps. Three robust lifecycle/two clear_tid conditional cases reject earlymarker as exactexit/FDreceipt.235candidate untouched, admissionfailed. Next review closed-child-domain isolated collector, not implemented. No device/root;16requirements/formal0.4/0.5 unchanged.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('236从保存7.02内核原字固定291分派/9表项/41269符号及单次wait对象引用，99静态检查、18代码范围、10源码段；12未门控排序1误认，3普通门控排序无误认，但另4身份反例保留首次查询前SIGKILL/用户标志过早/中断重查等缺口。3robust生命周期与2clear_tid条件拒绝提前标记充最终退出/FD归还。235原候选未改且准入仍失败，下一步审查封闭子进程域的隔离监管者，未实现；16/195/正式包保留，无设备/root。')
ev=dict(readme=rel+'/README.md',static_audit=rel+'/kernel-interface-audit.json',original_spans=rel+'/original-selected-spans.json',finite_model=rel+'/wait-reference-model-receipt.json',modern_numbers=rel+'/modern-number-crosscheck.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage236_saved_kernel_unique_exit_interfaces']=ev;new['recovery_saved_kernel_unique_exit_interfaces']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['优先审查隔离监管进程及其封闭子进程域：单线程、不收养无关后代、只创建本次工作器，核对实际fork/signal/父关系与收养代码；尚未实现，不以现代pidfd接口套给291项普通分派的保存内核。','单次wait确实固定structpid，但首次取引用前SIGKILL/外部回收及中断后重查仍有错对象反例；3普通门控排序无误认不是完整准入。用户态entered标志不充内核取引用完成，不阻塞Sony服务无限等待。','235原二进制与误认exit68为外国exit0反例保持，不能投放。robust OWNER_DIED也可能exec触发且早于exit_files；planned0加DONE不能识别随后SIGKILL，不接提前标记为成功。','身份/入口解决后整合完整boot采集和主机回传，同机健康备份/独立AP救砖逆写冷启动及MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16项继续。195root01未批准不启动，正式0.4/0.5和23源码不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert prior[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3保存内核的唯一退出接口](<'+rel+'/README.md>)：99静态检查/18代码范围固定291分派及单次wait对象引用；12调度1误认，3普通门控无误认但另4身份反例未解，提前futex通知不充最终退出/FD归还。转查封闭子进程域监管者，235准入仍失败；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage236-saved-kernel-unique-exit-audit-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
