"""Verify source bindings and register bounded restart findings, without device access."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from copy import deepcopy
from datetime import datetime,timezone
import json,os,stat,re,plistlib,subprocess,importlib.util,sys
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage201-updater-request-endpoint';REL=str(H.relative_to(R))
PREV='08c7bc10dbc875003a24c4996665f276a219d119ab86218cda30564fdd528b4b';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();assert digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text())
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
assert len(prior['files'])==61
reader=B/'stage2/extraction/read_filesystems.py';assert digest(reader)=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
sp=importlib.util.spec_from_file_location('saved_ext2',reader);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
f=m.Ext2(B/'stage2/extraction/nflasha15.img');assert sha256(f.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5';inv={x['path']:x for x in f.walk()}
captured=json.loads((H/'source-capture.json').read_text());assert len(captured)==4
for row in captured:
    p=Path(row['output']);p=p if p.is_absolute() else R/p;raw=p.read_bytes()
    assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'];assert f.data(inv[row['path']]['inode'])==raw
f.b.close();f.f.close()
sys.path.insert(0,str(R/'outputs/fx3-recovery-adapter'))
from fx3_recovery.fat import FatP1
from fx3_recovery.squash import SquashFS
scripts=json.loads((H/'historical-reboot-scripts.json').read_text());helpers=json.loads((H/'historical-reboot-helpers.json').read_text())
for s in scripts:
    src=Path(s['source_p1']);assert digest(src)==s['source_sha256'];fs=SquashFS(FatP1(src.read_bytes()).contents('/boot/initrd.img'));iv={x['path']:x for x in fs.walk()}
    p=Path(s['output']);assert p.stat().st_size==s['bytes'] and digest(p)==s['sha256'];assert fs.contents(iv[s['member']])==p.read_bytes()
    if '/2.05/' in str(src):
        for row in helpers:
            p=Path(row['output']);assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'];assert fs.contents(iv[row['member']])==p.read_bytes()
vendor=json.loads((H/'vendor-source-restart-locators.json').read_text());assert digest(Path(vendor['archive']))==vendor['sha256']
for row in vendor['matches']:
    p=Path(row['path']);p=p if p.is_absolute() else R/p;assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
proof=json.loads((H/'restart-route-proof.json').read_text());assert len(proof['selected_original_ranges'])==18 and proof['raw_check_count']==11
for row in proof['selected_original_ranges']:
    p=Path(row['source']);raw=p.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];a,z=int(row['start'],16),int(row['end_exclusive'],16);e=ELFFile(BytesIO(raw))
    if row['section']:part=e.get_section_by_name(row['section']).data()[a:z]
    else:
        s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']);off=s['p_offset']+a-s['p_vaddr'];part=raw[off:off+z-a]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
assert proof['current_AP_restart_request']['logical_queue']=='0x80920021' and proof['historical_p1_reboot']['logical_frame']==[17,3]
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link:assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='CURRENT_AP_RESTART_REQUEST_BOUND_TO_UPM_NOT_INDEPENDENT_RECOVERY',
  new_facts=['current libObj hot/cold requests use16B message0x00920141 toqueue0x80920021; current UPM receive thread and state-specific consumers located',
    'SEN604 command1 mode setup and command5 script request separated; no script in selected current shipped inventories, historical p1 has it',
    'historical p1 script runs PD helper b thenud_reboot; ELF entry binds main and powerIC7 branch constructs128B frame11/3, separate from11/4 update',
    'GPL7.00 registers GPIO reset hook but exact7.02 runtime mapping not established; latest web-read community SD recovery still assumes Fastboot'],
  limits=['current update-preparation caller connection to hot/cold wrappers unproven; enqueue0 is not actual reboot',
    'UPM needs live threads/state/semaphores; historical helper needs running AP Linux/SIO/GPIO/Backup, not AP bootstrap',
    'absence only in selected package inventories; current installed p1 and runtime staging not read',
    'no measured power/reset, p1/p3 boot selection, independent inverse restore, target HEVC recording or long-record receipt'],
  scope_counts=dict(current_AP_original_files=4,historical_scripts=2,historical_helpers=2,selected_original_ranges=18,raw_checks=11),
  prior_turn_classification='progress, previous seal61verified and endpoint business consumer established',
  exploratory_locator_warning='UPM .rodata name table and WFI filtered contexts are not executable recovery entry evidence; API errors are not negative availability proof',
  root01='same195 pending specific reply, no job or admin launch; no repeated question',original_or_guest_executions=0,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_SOURCE_BOUND_UPDATE_RESTART_REVIEW',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=61,
  selected_original_ranges=18,raw_checks=11,current_AP_files_reverified_against_image=4,historical_scripts_and_helpers_reverified_against_p1=4,
  host01_bundle_sha256_unchanged=HOST,release0_4_zip_unchanged=True,new_approval_granted=False,actual_device_reboot_observed=False,original_or_guest_executions=0,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
  research_activity='Bound current7.02 libObj hot/cold requests to exact UPMqueue21 receive thread/off-factor state handling. SEN604 mode/reboot commands separated; script unavailable in checked current shipped inventories but historical p1 helper uses Darwin11/3.18source ranges/11raw checks; no original/guest/root/device actions. No independent AP boot selector or restore receipt.195 still pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('202当前hot/cold消息→UPMqueue21接收→off状态分派已绑定；604命令1/5分开，当前已查包无us_reboot而历史p1有，历史helper发送11/3。18原范围/11编码核对；GPL复位未绑当前，社区仍需Fastboot。无guest/root/设备，195待答，16要求/授权不变；下一项WBI物理范围与早启原件。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',restart_proof=REL+'/restart-route-proof.json',script_availability=REL+'/reboot-script-availability.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',original_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage202_current_and_reference_reboot_routes']=ev
new['recovery_update_restart_route']={**ev,'current_AP_request_to_UPM_consumer_located':True,'update_preparation_to_actual_restart_caller_proven':False,'actual_device_reboot_observed':False,'historical_Darwin_reboot_frame':[17,3],'AP_p1_p3_boot_selection_proven':False,'independent_restore_proven':False}
new['next_safe_offline_actions']=[
 '195仅主机root01的原具体问题待答，不视继续为批准、不创建或启动固定作业、不重问。',
 '当前模式写入、hot/cold入队与UPM状态处理、历史p1重启11/3分别已定位；不再泛扫同一路径或将任何返回0当硬件/冷启动完成。',
 '核对公开WBI格式与其保存的物理内存范围，确定是否已有可还原的AP早期装载原件；若不包含，明确缺失的原机启动来源。保留同机启动备份、独立逆写/冷恢复和MAIN1080p29.97 HEVC等16项；新设备动作仍需对应授权。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').write_bytes(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').write_bytes(ib);marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3重启请求与恢复环境依赖](<'+REL+'/README.md>)：7.02 hot/cold已追至UPM队列接收/状态机；604脚本路径与历史p1重启11/3分开，18原范围/11编码核对；尚非AP独立自举，195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').write_bytes(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name in [(canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')]:
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage202-restart-route-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=61,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,new_approval_granted=False,original_or_guest_execution=False,root_or_device_operations=0,native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0,goal_complete=False,persistent_write_release=False)))
