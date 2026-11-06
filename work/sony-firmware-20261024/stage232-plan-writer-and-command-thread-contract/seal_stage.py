"""Seal static provisioning/thread evidence without releasing device work."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,io,json,os,plistlib,stat,subprocess
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage231-constructor-noexec-child-and-reload-observer';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def load(p):return json.loads(p.read_text())
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='85326100f4abf29a0310efc76d48c5f1007582238d7af4494200552d8fd8e311'
pm=load(P/'final-receipt.json');assert len(pm['files'])==125
for row in pm['files']:
 p=R/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
a=load(H/'contract-audit-final.json');assert len(a['images'])==2 and a['source_only'] and not a['original_Sony_glibc_Linux_or_public_camera_code_executed'] and a['new_device_USB_cache_admin_auth_upload_firmware_or_WBI_operations']==0 and not a['first_flash_released']
assert len(a['mode_gaps'])==2 and all(not x['explicit_mode_assignment'] and not x['actual_register_value_or_created_mode_known'] for x in a['mode_gaps'])
assert a['writer']['new_wrapper_ordinary_file_mode_argument_not_established'] and not a['writer']['root0600_RAM_plan_creation_proven']
assert a['path']['absolute_outside_base_is_prefixed_not_passed_as_root_path'] and a['path']['ordinary_flash_mount_side_effect_not_removed'] and not a['path']['path_escape_is_currently_validated_safe_provisioning']
assert a['thread']['one_queue_does_not_prove_same_TID'] and a['thread']['kernel_callback_to_worker_assignment_not_yet_audited'] and not a['thread']['loosening_thread_guard_accepted']
assert not a['next_adapter']['preparer_implemented'] and not a['next_adapter']['preparer_deployable'] and a['next_adapter']['plan_START_to_OBSERVE_transition_and_host_receipt_readback_still_required']
functions=checks=whole=0
for image in a['images']:
 p=R/image['path'];raw=p.read_bytes();assert len(raw)==image['bytes'] and sha(p)==image['sha256'];e=ELFFile(io.BytesIO(raw))
 def read(va,n):
  s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']);at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n]
 for f in image['functions_and_slices']:
  va=int(f['VA'],16);data=read(va,f['bytes']);assert data.hex()==f['original_hex'] and sha256(data).hexdigest()==f['sha256'] and len(f['instructions'])*4==f['bytes'];functions+=1
  if f['boundary']=='dynamic symbol full function':whole+=1
  for n,i in enumerate(f['instructions']):assert int(i['pc'],16)==va+n*4 and read(va+n*4,4).hex()==i['raw']
 for x in image['manual_checks']:assert read(int(x['pc'],16),4).hex()==x['raw'];checks+=1
 if p.name=='libJiritsu.so':
  f=next(x for x in e.get_dwarf_info().EH_CFI_entries() if isinstance(x,FDE) and x['initial_location']==0xb278);assert f['address_range']==0x25c
assert (functions,whole,checks)==(15,10,46)
r=load(P/'runs-bounded-verified/receipt.json');assert r['status']=='PASS' and r['tests_run']==14 and len(r['cases'])==22
for name in ['other-thread','reused-thread-number']:
 c=next(c for c in r['cases'] if c['name']==name);assert c['observations']==[2] and not c['waits']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='STATIC_WRITER_AND_RECEIVE_THREAD_CONTRACT_AUDITED_NOT_DEPLOYABLE',original_images=2,dynamic_symbol_complete_functions=10,original_FDE_complete_callback=1,explicit_slices=4,manual_instruction_checks=46,ordinary_wrapper_creation_mode_gaps=2,root0600_RAM_plan_provisioning_verified=False,same_live_creator_thread_assignment_verified=False,preparer_implemented=False,preparer_deployable=False,actual_device_runtime_or_recovery_verified=False,original_Sony_glibc_Linux_or_public_camera_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:231 sealed own constructor NOOP lifecycle and22 modeled scenarios',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=125,current_audit_sha256=sha(H/'contract-audit-final.json'),source_byte_slices_and_FDE_rebound=True,unchanged231_tests_not_rerun=True,**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Static writer/thread feasibility audit:2 original images,10symbol whole functions+1FDE whole callback+4explicit slices,46checks. Old setter requests0755 before unknown umask/ACL; new CFileAccess ordinary open paths do not establish required creation-mode register after intervening calls. get_access_filename prefixes outside absolute paths under fixed /tmp/jiritsu or/mnt, so plain root RAM plan path is not a proven host target; ordinary flash mount side effect remains. Queue016f0480 takes UIPC ioctl registration, conditional receiver-pool creation and shared-fd callback loop; actual kernel queue/thread assignment still unknown. Preserve231same-thread rejection. Next design full fixed RAM plan creator with embedded workerSHA/nonce/associations and target monotonic clock; empty precreation alone insufficient. No adapter implemented or device/root operations; full16requirements/formal sources preserved.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('232固定两个原件/10动态符号完整函数+1原FDE回调+4切片/46核对：旧写入请求0755但umask/ACL未知，新包装器两处open在外部调用后未建立创建mode；任意绝对RAM路径会加固定基目录，预建空文件加普通填充路线不完整。016f0480走UIPC接收池，真实内核分配未核，不承诺同TID，保留231保护。下一版研究自写程序内完整生成0600 RAM计划、固定工作SHA/关联和目标单调时钟；转换/回传及线程分配待证。全16/195/正式包不变，无设备/root。')
ev=dict(readme=rel+'/README.md',audit=rel+'/contract-audit-final.json',source=rel+'/audit_contract.py',primary_references=rel+'/primary-reference-notes.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage232_writer_and_thread_contract']=ev;new['recovery_plan_writer_and_command_thread_contract']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['优先研究受限自写准备程序：包含固定工作程序SHA、nonce和关联字段，自采目标CLOCK_MONOTONIC，以核验RAM目录/EXCL/NOFOLLOW/root0600一次生成完整计划；先设计、构建和模型验证，不上传。','补完整计划START到OBSERVE转换及主机可复核回执路线；普通外部RAM路径有基目录拼接，不能靠猜mode或未经完整核验的祖先路径充安全投放，flash挂载前置不隐去。','继续核对UIPC接收ioctl的内核队列/线程索引分配规则及实际可达性；同队列不充同TID，保留231活创建线程/proc锚/WNOTHREAD保护，跨线程替代必须另证PID复用安全。','整合完整boot备份与独立完成仍待入口合同解决；同机完整健康备份/独立AP救砖逆写冷启动/实际MAIN1080p29.97 HEVC42010约16Mbps、exact30及音画长录16要求保持。195root01未批准不启动，正式0.4/0.5不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3任务文件投放与接收线程合同](<'+rel+'/README.md>)：2原件/11完整函数及回调/4切片/46核对，发现包装器创建mode未建立、外部绝对路径加基目录；UIPC条件接收池不充同TID。转向完整RAM计划自生成和内核线程分配核对，现231保护保留；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage232-plan-writer-and-thread-contract-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
