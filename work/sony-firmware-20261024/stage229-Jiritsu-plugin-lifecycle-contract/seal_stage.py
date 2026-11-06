"""Seal the static plugin ABI audit; no device/test launch operations."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage228-real-entrypoint-portability-audit';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='3ccae9487a0c2aa1c1f2b33669af0c223bfe6a95bc18ec2d8cec856945d244d5'
pm=json.loads((P/'final-receipt.json').read_text());assert len(pm['files'])==21
for row in pm['files']:
 p=R/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
a=json.loads((H/'plugin-lifecycle-audit.json').read_text());assert a['whole_functions_rebound']==8 and len(a['manual_PLT_checks'])==22 and len(a['ABI_instruction_checks'])==29 and len(a['independent_ADRP_ADD_symbol_checks'])==4
source=R/a['source']['path'];assert sha(source)==a['source']['sha256'] and source.stat().st_size==225200
assert not a['Sony_or_Linux_code_executed'] and not a['new_camera_operations'] and not a['first_flash_released']
assert a['lifecycle']['stop_counter']==31 and a['lifecycle']['maximum_requested_sleeps_before_timeout']==30 and a['lifecycle']['sleep_argument_microseconds']==100000 and a['lifecycle']['stop_timeout_or_enqueue_failure_writes_state']==30
assert not a['lifecycle']['stop_has_thread_join_or_kill_or_dlclose'] and not a['lifecycle']['state10_is_actual_thread_exit_proof'] and not a['lifecycle']['exit_checks_wait_return_before_clearing_handle']
assert a['queue_contract']['borrowed_pointer_offsets']==[8,16,24] and not a['queue_contract']['deep_copy_of_queued_strings_in_sender'] and not a['plugin_contract']['full_object_or_Run_context_layout_recovered']
reference=B/'stage189-TERM_MODE-consumer/fixed-loader-prefix-results.json';assert json.loads(reference.read_text())['source_sha256']==sha(source)
provenance=B/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/sources.json';assert any(x['sha256']==sha(source) for x in json.loads(provenance.read_text())['sources'])
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='STATIC_ACTUAL_PLUGIN_ABI_AND_STOP_COMPLETION_LIMITS_PINNED',original_whole_functions=8,manual_PLT_checks=22,ABI_instruction_checks=29,symbol_string_address_checks=4,queue_only_borrowed_pointers=True,RunScriptI_synchronous_on_service_thread=True,stop_state_or_timeout_is_thread_exit_proof=False,actual_thread_or_plugin_or_USB_completion_verified=False,new_device_admin_auth_upload_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=21,source_sha256=sha(source),source_provenance_sha256=sha(provenance),prior_mount_evidence_sha256=sha(reference),failed_audit_causes=['operandless ret whitespace','relative path reporting'],original_code_executed=False,**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Static actual Jiritsu route audit:8complete functions,22PLT/29ABI/4string address checks. Create/Load/Run/DestroyScriptI require object and partial0x18f8 Run context, not227step exports.32B queued messages borrow3pointers; run queues load then run but does not await execution. Synchronous RunScriptI can delay same-thread stop. stop op3 polls31 counter/30x100000us then state30; no join/kill/dlclose. State10 store precedes final ret; exit wait return unchecked before handle clear. Parent flash mount/release precedes5MiB child tmpfs copy. Full plugin layout/real loader/runtime/recovery still missing; no camera or root operations.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress:228 ordinary loader thread mismatch and public recovery refresh'
new['progress_audit']['basis'].append('229按真实Jiritsu路线补8完整原函数/22调用/29ABI/4字符串地址：明确工厂对象与0x18f8运行上下文、队列借用指针、run只排队、同步插件阻塞可延迟同线程stop。stop超时状态30且无join，状态10先于ret；exit等待返回未检查即清句柄。最终5MiB tmpfs复制不充此前flash挂载/旧插件释放无副作用。未生成/上传插件或放宽guard，16要求/195/正式包保持。')
ev=dict(readme=rel+'/README.md',audit=rel+'/plugin-lifecycle-audit.json',functions=rel+'/selected-functions.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage229_Jiritsu_lifecycle']=ev;new['recovery_Jiritsu_plugin_lifecycle_contract']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['真实Jiritsu插件对象/Run上下文、调用数据存活和独立完成证明仍缺；先完成具体合同或找到可达的独立子进程入口，不直接将227step模块改名上传、不放宽身份/主线程检查。','已核普通路径父flash挂载/旧插件释放及同步Run阻塞stop；设计首次采集入口时必须明确这些副作用和超时UNKNOWN，不用run/stop状态或wait后清句柄作为释放证明。','针对其余真实入口与同机备份数据路径继续静态审查；旧固定DEBUG日期/TERM_MODE/Jiritsu普通写入已有限定拒绝，避免重复模型测试代替入口或独立AP恢复。','保留16完整要求与MAIN1080p29.97 HEVC42010约16Mbps/exact30单列；实际成片音画长录/健康完整备份/访问归还/独立救砖/逆写冷启动仍缺；195root01未批准不启动或重问，无新增设备权限。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3服务插件接口与停止完成条件](<'+rel+'/README.md>)：8完整原函数/22调用/29ABI/4字符串核对，实际Create/Load/Run/DestroyScriptI对象及0x18f8上下文未适配；run排队/stop状态10或超时30不充线程结束，exit等待返回未检查即清句柄。父flash前置与5MiB子tmpfs分开，无设备/root，仍不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage229-Jiritsu-lifecycle-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
