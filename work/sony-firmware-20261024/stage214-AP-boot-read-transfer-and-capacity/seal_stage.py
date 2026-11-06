"""Verify and register source-only transfer contract without changing grants."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess,tarfile
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R))
P=B/'stage213-AP-eMMC-boot-asset-search'
PREV='ac310d1710a0d2be0eb6b1d2bc5733d9de0a4488a0839cc0b1e28386be60ebaf'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(name,value):(H/name).open('x').write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==61
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
proof=json.loads((H/'AP-transfer-and-capacity-proof.json').read_text())
src=R/proof['source'];assert digest(src)==proof['source_sha256']=='14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d'
with src.open('rb') as f:
    e=ELFFile(f)
    for row in proof['raw_ranges']:
        sec=e.get_section_by_name(row['section']);raw=sec.data()[row['start']:row['end_exclusive']]
        assert raw==(R/row['raw']).read_bytes() and len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256']
        assert row['file_offset']==sec['sh_offset']+row['start']
assert len(proof['raw_ranges'])==24 and len(proof['source_lines'])==5
for row in proof['source_lines']:assert (H/row['path']).read_text().splitlines()[row['line']-1]==row['text']
assert proof['capacity']['source_register']=='EXT_CSD[226] BOOT_MULT' and proof['capacity']['actual_body_value'] is None
assert proof['read_view']['controller_optional_reset_transfer_wait_callbacks_skipped_when_null']
assert not proof['read_view']['actual_body_bytes_or_end_to_end_raw_restore_verified']
assert proof['access_switch']['access_selection_state_may_change_during_file_read']
assert proof['access_switch']['error_paths_include_kernel_panic']
examples=json.loads((H/'access-switch-source-derived-examples.json').read_text());assert len(examples['examples'])==9
assert all(not x['actual_device_test'] for x in examples['examples'])
gpl=json.loads((H/'GPL-MMC-source-capture.json').read_text());archive=R/gpl['archive']
assert digest(archive)==gpl['archive_sha256']=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
want={x['member']:x for x in gpl['files']};assert len(want)==2
found=0
with tarfile.open(archive,'r:gz') as tf:
    for m in tf:
        if m.name in want:
            row=want[m.name];raw=tf.extractfile(m).read()
            assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'] and raw==(R/row['output']).read_bytes();found+=1
assert found==2
candidate=json.loads((H/'AP-boot-read-candidate-refinement.json').read_text())
for k in ['executable','new_device_backend','camera_operation_authorized','persistent_write_release']:assert not candidate[k]
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-recheck.json').read_text())
manual=json.loads((H/'manual-continuation-receipt.json').read_text())
assert native['goal']['status']=='blocked' and manual['latest_user_request']=='继续'
assert manual['manual_offline_research_continuation_authorized'] and not manual['new_device_authorization_inferred']
assert len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('verification-receipt.json',dict(status='PASS_STATIC_CAPACITY_CRYPTO_CONTEXT_AND_PARTITION_ACCESS_PROOF',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=61,source_module_sha256=proof['source_sha256'],
    original_section_ranges=24,standard_source_lines=5,raw_word_checks=9,relocation_checks=6,
    optional_crypto_context_skip_branches=3,source_derived_access_examples=9,
    GPL_reference_files_reextracted=2,capacity_register=226,capacity_actual_value_measured=False,
    partition_access_state_change_path_identified=True,panic_failure_paths_identified=True,
    actual_body_read_or_restore_tested=False,root01_bundle_unchanged=True,root01_job_absent=True,
    release04_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
    Sony_code_or_guest_execution=False,root_or_device_operations=0,persistent_write_release=False))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='blocked',
    goal_manager_status_last_observed='blocked',native_goal_state_not_modified=True,
    research_activity='Bound cached CMD8 EXT_CSD[226] copy to boot capacityu8<<17. Traced null optional decrypt context through single/multi request, sequence/host ops and controller3skip branches. CMD6 access selection uses CLR_BITS2/SET_BITS1,index179,masks0/1/2; file read may change card access state and selected failures panic.24raw ranges,5standard lines,9word/6reloc checks;9illustrative bit examples only. No Sony/guest/root/device action;195 pending,16requirements and0.4 unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-recheck.json',observed_utc=native['observed_utc'],status='blocked',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='继续',receipt=REL+'/manual-continuation-receipt.json',
    classification='progress',native_status_remains='blocked',fresh_blocked_audit=True,
    same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('214绑CMD8缓存EXT_CSD[226]→状态dc→u8<<17容量；单/多块空解密上下文经实际ops重定位到控制器3处跳过回调。读启动区可发CMD6切访问选择179，CLR2/SET1掩码0/1/2；特定失败和高位guard有panic，不能描述为全设备状态不变。24原范围/5标准行/9原字+6重定位，9按位例只属说明；无设备/root/guest，16要求、195待答和0.4不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',proof=REL+'/AP-transfer-and-capacity-proof.json',
    examples=REL+'/access-switch-source-derived-examples.json',candidate=REL+'/AP-boot-read-candidate-refinement.json',
    GPL=REL+'/GPL-MMC-source-capture.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',
    Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage214_AP_boot_read_transfer_and_capacity']=ev
new['recovery_AP_boot_read_transfer_and_capacity']={**ev,
    'boot_capacity_source_register':226,'formula':'unsignedEXT_CSD[226]<<17','actual_geometry_bytes':None,
    'selected_driver_optional_decrypt_context_path_bound':True,'controller_NULL_skip_branches':3,
    'actual_body_read_view_or_restore_verified':False,'partition_access_select_register':179,
    'read_may_issue_MMC_SWITCH_access_selection':True,'selected_error_paths_include_kernel_panic':True,
    'previous_access_restore_after_read_proven':False,'independent_AP_boot_or_same_body_restore_proven':False}
new['recovery_AP_boot_devices_and_capacity']['stage214_refinement']={
    'evidence':REL+'/AP-transfer-and-capacity-proof.json','standard_capacity_register':226,
    'selected_optional_decrypt_callback_path_now_bound':True,
    'actual_whole_boot_view_or_restore_still_unverified':True,
    'file_read_may_change_hardware_partition_access_state':True}
new['provenance_refinements'].append(dict(stage214_file_read_protocol_scope=True,
    evidence=REL+'/AP-transfer-and-capacity-proof.json',selected_file_read_not_whole_device_state_free=True,
    mode1_and2_only_change_selected_low_access_bits=True,actual_device_commands_sent=0))
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答；不将继续当批准，不启动或重问，不扩大相机权限。',
    '将当前AP启动区动态容量与设备/执行环境身份、所选无解密回调视图和UNKNOWN失败收据接入受限采集工作器的源码候选及主机后端；不添加自动相机入口，实际p1驱动身份未验不能套主系统哈希放行。读取范围说明必须包括可能的MMC_SWITCH访问选择和panic分支；不能假称结束后已恢复选择。',
    '保持同机boot0/p1/完整配置、独立AP入口、逆写/冷启动/故障恢复缺口及16要求和真实MAIN1080p29.97 HEVC长录验收；代码/主机验证不充机身备份或恢复证明，旧0.4及其硬件未验状态保留。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[k]==old[k],k
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3启动区读取与访问状态](<'+REL+'/README.md>)：容量EXT_CSD226×128KiB和空解密上下文至控制器3处跳过已绑；读取可发CMD6选179访问位，特定失败panic，实际数据视图/恢复未验。24范围/5标准行，195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage214-AP-boot-transfer-capacity-v1',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=61,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
    root01_bundle_sha256_unchanged=HOST,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='blocked',manual_continue_request_processed=True,native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),raw_ranges=24,
    standard_lines=5,raw_word_checks=9,relocation_checks=6,requirements_unchanged=16,authorizations_unchanged=True,actual_device_operations=0)))
