"""Seal static ET_REL dispatch and conditional own-ARM64 receiver evidence."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,io,json,os,plistlib,stat,subprocess
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage232-plan-writer-and-command-thread-contract';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def load(p):return json.loads(p.read_text())
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='be6c85c68c441c6370eb175fa894c3c12288a523ec75f4f6b4c25e2b29bcd22c'
pm=load(P/'final-receipt.json');assert len(pm['files'])==13
for row in pm['files']:
 p=R/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
a=load(H/'kernel-assignment-audit-final.json');src=R/a['source']['path'];raw=src.read_bytes();assert sha(src)==a['source']['sha256']=='6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38' and len(raw)==a['source']['bytes']
elf=ELFFile(io.BytesIO(raw));assert elf['e_type']=='ET_REL';text=elf.get_section_by_name('.text').data();assert len(a['slices'])==5 and len(a['manual_instruction_checks'])==54 and len(a['dispatch_table'])==17
for f in a['slices']:
 va=int(f['VA'],16);data=text[va:int(f['end'],16)];assert len(data)==f['bytes']==len(f['instructions'])*4 and data.hex()==f['original_hex'] and sha256(data).hexdigest()==f['sha256']
 for n,i in enumerate(f['instructions']):assert int(i['pc'],16)==va+4*n and data[n*4:n*4+4].hex()==i['raw']
for x in a['manual_instruction_checks']:
 va=int(x['pc'],16);assert text[va:va+4].hex()==x['raw']
rels={};symtab=elf.get_section_by_name('.symtab')
for section in elf.iter_sections():
 if section['sh_type']!='SHT_RELA':continue
 target=elf.get_section(section['sh_info']).name
 for r in section.iter_relocations():
  s=symtab.get_symbol(r['r_info_sym']);idx=s['st_shndx'];rels[target,r['r_offset']]=dict(owner_section=target,offset=hex(r['r_offset']),type=r['r_info_type'],symbol=s.name,symbol_value=hex(s['st_value']),symbol_section=elf.get_section(idx).name if isinstance(idx,int) else idx,addend=r['r_addend'])
for row in a['dispatch_table']:
 x=row['entry'];assert x==rels[x['owner_section'],int(x['offset'],16)]
for x in a['selected_literal_relocations']:assert x==rels[x['owner_section'],int(x['offset'],16)]
for x in a['manual_instruction_checks']:
 if 'relocation' in x:assert x['relocation']==rels['.text',int(x['pc'],16)]
assert a['dispatch_table'][13]['entry']['addend']==0x890 and a['dispatch_table'][8]['entry']['addend']==0xe90 and a['registration']['CB_context30_stores_same_handle_context'] and a['worker_slots']['count']==4
assert not a['original_Sony_Linux_or_kernel_module_executed'] and a['new_device_operations']==0 and not a['first_flash_released']
rr=load(H/'receiver-schedule-results.json');rebind=load(H/'source-rebinding.json');initial=load(H/'kernel-assignment-audit.json')
assert rr['status']==rebind['status']=='PASS' and rr['schedules']==len(rr['cases'])==16 and rr['same_slot_observed']==4 and rr['different_slot_HELD48']==12
assert rr['source_audit_sha256']==sha(H/'kernel-assignment-audit.json')==rebind['executed_schedule_source_sha256'] and rebind['final_audit_sha256']==sha(H/'kernel-assignment-audit-final.json')
assert rr['script_sha256']==sha(H/'check_receiver_schedules.py') and rr['own_binary']['sha256']==sha(R/rr['own_binary']['path'])=='c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec' and rr['own_model']['sha256']==sha(R/rr['own_model']['path'])
assert initial['source']==a['source'] and initial['worker_slots']==a['worker_slots'] and initial['queue_algorithm']==a['queue_algorithm'] and initial['dispatch_table']==a['dispatch_table']
for f in initial['slices']:assert f==next(x for x in a['slices'] if x['VA']==f['VA'])
assert not rr['actual_active_count_or_scheduler_measured'] and not rr['whole_kernel_or_ioctl_or_driver_simulated'] and rr['only_own_ARM64_executed'] and not rr['actual_Linux_processes_or_threads_created'] and rr['new_device_operations']==0 and not rr['existing231_thread_guard_removed']
for c in rr['cases']:
 assert c['own_child_exit']==0 and c['child_original_file_mappings_removed'] and len(c['synthetic_trace'])==4
 if c['first_slot']==c['second_slot']:assert c['observation']==[3,0] and len(c['waits'])==1 and c['waits'][0]['status']==0
 else:assert c['observation']==[2,48] and not c['waits']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='KERNEL_SHARED_CALLBACK_FIFO_AND_TASK_SLOTS_PINNED_231_GUARD_PRESERVED',original_kernel_module=1,explicit_static_slices=5,manual_instruction_checks=54,dispatch_entries=17,supported_receiver_slots=4,conditional_receiver_schedules=16,same_slot_observed=4,cross_slot_HELD48=12,actual_current_receiver_count_or_scheduler_measured=False,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,current231_binary_and_guards_unchanged=True,plan_preparer_implemented=False,probe_deployable=False,actual_device_backup_or_recovery_verified=False,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:232 sealed writer/path/receive-thread contract evidence',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=13,source_section_bytes_and_relocations_rebound=True,source_audit_sha256=sha(H/'kernel-assignment-audit-final.json'),own_binary_sha256=rr['own_binary']['sha256'],unchanged231_full_tests_not_rerun=True,**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Kernel UIPC ET_REL branch pinned:5explicit slices/54instruction-relocation checks/17dispatch entries. ioctl8000000d selects.text890; registration index8 stores same handle atCB30 and separate queue ID. Context38 FIFO tail append/head pop under lock, four task-bound receiver slots, wake scan across all. No queue affinity established in pinned branch; actual active count/configuration not measured.16conditional FIFO schedules execute sealed231own ARM64 only:4same-slot observed,12cross-slot HELD48 before wait; child exits0 in all. Existing thread/proc/WNOTHREAD guards and binary preserved. Next fixed full RAM plan preparer and same-constructor bounded observation feasibility; do not assume same queue implies sameTID or weaken PID protection. No device/root operations;16requirements/formal sources unchanged, not deployable.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('233核回232的13成员，追到内核osal_uipc原件：5切片/54指令重定位/17分派，注册CB30存同一handle、队列号另存；ioctl0d到890按4个任务槽领取context38共享FIFO，入队扫描唤醒全部睡眠槽。实际线程数未测，多接收槽时同队列不充同线程。16条件调度执行未改231自写ARM64，4同槽通过、12跨槽HELD48且不wait，child均exit0，保留线程/PID保护。转向完整RAM计划准备及同次加载有界观察合同，不重复231全套；16/195/正式包不变，无设备/root。')
ev=dict(readme=rel+'/README.md',audit=rel+'/kernel-assignment-audit-final.json',source=rel+'/audit_kernel.py',schedules=rel+'/receiver-schedule-results.json',schedule_source=rel+'/check_receiver_schedules.py',source_rebinding=rel+'/source-rebinding.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage233_kernel_receiver_assignment']=ev;new['recovery_kernel_UIPC_callback_slot_assignment']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['实现并离线验证固定RAM计划准备程序：嵌入固定工作SHA/nonce/关联字段，自采目标单调时钟并以EXCL/NOFOLLOW创建root0600完整计划；先完成自身镜像/进程绑定、限长/时钟/权限/错误清理合同，不上传。','优先核对同一次构造加载内完成有界任务和独立退出观察的请求时限、同步返回、停止/超时及失败保留条件；不要依赖下一次请求回到同线程，也不删除231活线程/proc锚/WNOTHREAD。','若改跨线程观察或常驻监管，须另外证明精确子身份/退出/资源归还，保留PID复用反例；不能用PID消失、文件存在或仅DONE取代。完成计划转换与主机回传仍缺。','入口合同解决后整合完整boot采集、同机健康备份及独立AP恢复/逆写冷启动；MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录等16要求不缩小，195root01未批准不启动，正式0.4/0.5不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3内核UIPC接收槽分配](<'+rel+'/README.md>)：驱动5切片/54核对/17分派固定共享回调FIFO与4任务槽，实际接收数未测；16条件调度运行原231自写ARM64，4同槽通过、12跨槽HELD48，保留退出身份保护。完整计划准备/入口备份恢复未验，无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage233-kernel-receiver-assignment-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
