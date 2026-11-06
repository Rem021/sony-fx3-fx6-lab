"""Seal new endpoint evidence; keep all existing device and release gates intact."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from copy import deepcopy
from datetime import datetime,timezone
import json,os,stat,subprocess,plistlib,re
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage200-official-Darwin-updater-dependencies';REL=str(H.relative_to(R))
PREV='ee031302fc65b97425c90fc7bde2bc1c1578ffd07620d406aa8ebe508e9f0aad';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();assert digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text())
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
assert len(prior['files'])==70
main=json.loads((H/'current-main-capture.json').read_text());refs=json.loads((H/'reference-providers.json').read_text())
assert digest(Path(main['source_image']))==main['source_image_sha256']
for row in main['captures']:
    p=Path(row['path']);assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
for row in refs['sources']:
    p=Path(row['path']);assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
for row in refs['captures']:
    p=Path(row['output']);assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
proof=json.loads((H/'queue-endpoint-proof.json').read_text());user=json.loads((H/'user-registration-proof.json').read_text());audit=json.loads((H/'endpoint-raw-audit.json').read_text())
selected=proof['selected_original_ranges']+user['selected_original_ranges'];assert len(selected)==12 and audit['check_count']==10
for row in selected:
    raw=(H/'originals/7.02-main'/row['source'].lstrip('/')).read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];e=ELFFile(BytesIO(raw));a,z=int(row['start'],16),int(row['end_exclusive'],16)
    if row['section']:part=e.get_section_by_name(row['section']).data()[a:z]
    else:
        s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']);off=s['p_offset']+a-s['p_vaddr'];part=raw[off:off+z-a]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
assert proof['registration']['callback']=='0xed990' and proof['registration']['api']=='osal_reg_msg_queue_cb'
assert proof['callback_effects']['accepted_normal_paths']=={'0':[],'2':['mode'],'3':['mode','mode3'],'4':['mode','mode1'],'6':['mode','mode6']}
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link:assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
assert len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='CURRENT_7_02_QUEUE_BUSINESS_CALLBACK_LOCATED_FLAGS_NOT_INDEPENDENT_BOOTSTRAP',
    previous_synthesis_correction='183 high-id evidence already had libObj registration site; this stage follows exact PLT and callback and supersedes unresolved-consumer summary',
    positive_facts=['udtr_senser_init conditionally registers0x004b0376 -> callback0xed990 in current libObj',
      'actual user ioctl registration and kernel low16 local send match0x0376; high bit difference is not another queue',
      'callback requests removal of mode flags and conditionally creates mode/mode1/mode3/mode6; open has create/write access',
      'normal cases0/2/3/4/6 differ from script5/7; helper receive0/-1022 does not certify business success or cold boot'],
    limits=['runtime registration and service life not observed; callback depends on main AP/libObj context',
      'ordinary selected paths and effects only, no actual file writes/durability/reboot or partition load',
      'reference p1 binaries not current installed p1; some2.04/2.05 kernel differences exceed build-id',
      'same-body p1/boot0 backup, independent inverse write, cold recovery and MAIN HD HEVC/long-record acceptance remain unverified'],
    source_counts=dict(current_main_files=6,historical_provider_files=12,selected_original_slices=12,independent_raw_checks=10),
    exploratory_locators_only=['avcam-register-locators.txt','avcam-receive-locators.txt','avcam-dynamic-id-locators.json','osal-init-locators.txt','reference-p1-osal-send.txt','reference-p1-user-send.txt','reference-p1-delivery.txt'],
    root01='same195 specific question pending; no job, launch or repeat question',original_or_guest_executions=0,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_STATIC_CURRENT_ENDPOINT_AND_WRITE_BOUNDARY_REVIEW',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=70,
    current_main_originals=6,historical_reference_originals=12,selected_original_slices_reverified=12,independent_raw_branch_checks=10,
    host01_bundle_sha256_unchanged=HOST,release0_4_zip_unchanged=True,new_approval_granted=False,actual_registration_or_cold_recovery_observed=False,original_or_guest_executions=0,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,
    research_activity='Located actual current7.02 queue0x376 business callback in libObj0xed990 via conditional udtr_senser_init and exact PLT relocation. It changes mode files; normal0/2/3/4/6 paths do not prove AP restart/p1 load. Script5/7 can hit a cleared-flags/no-normal-reply path while helper accepts receive-1022.12source slices/10raw checks; no original/guest/root/device actions. Correct183 unresolved-consumer synthesis;195 still pending.',
    goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True)
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('201从183既有libObj高ID线索补齐当前7.02真正queue0x376注册与回调；低16匹配，修改模式文件且非直接自举。0/2/3/4/6与5/7错路、辅助程序-1022正常结束边界已核；12原切片/10独立编码检查，历史p1供应者不替代当前。无guest/root/设备，195待答，全部16要求/授权不变。')
evidence=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',endpoint=REL+'/queue-endpoint-proof.json',user_registration=REL+'/user-registration-proof.json',raw_audit=REL+'/endpoint-raw-audit.json',capture=REL+'/current-main-capture.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',original_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage201_current_request_business_consumer']=evidence
new['recovery_queue0376_business_consumer']={**evidence,'actual_business_callback_source_located':True,'actual_runtime_registration_observed':False,'mode_file_persistent_write_path':True,'AP_restart_or_p1_load_proven':False,'independent_restore_proven':False,'supersedes_unresolved_synthesis_in_stage183':True}
new['next_safe_offline_actions']=[
 '195仅主机root01具体回答仍待用户；不把继续视为批准，不创建固定作业或启动管理员，不重复提问。',
 'queue0x376业务消费者已定位，不再重复泛扫；当前路径改持久mode文件且依赖libObj/im，不能当只读探测或独立救援。适配必须验证实际模式结果及重启后的状态，不能只用helper0。',
 '继续查明确的AP重启请求和早期p1/p3选择装载来源，区分设置mode与真正进恢复。保留同机启动原件/独立逆写/冷启动恢复及MAIN1080p29.97 HEVC等16项，任何新设备读取或模式动作需对应授权。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[k]==old[k],k
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').write_bytes(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').write_bytes(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3更新队列的实际接收者](<'+REL+'/README.md>)：7.02 libObj已绑定queue0x376实际回调，源码显示mode文件写入与5/7拒绝/超时掩盖；12切片/10编码核对，非AP独立自举；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').write_bytes(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name in [(canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')]:
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage201-business-endpoint-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=70,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,new_approval_granted=False,original_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),requirements_unchanged=16,all_authorizations_unchanged=True,goal_complete=False,persistent_write_release=False)))
