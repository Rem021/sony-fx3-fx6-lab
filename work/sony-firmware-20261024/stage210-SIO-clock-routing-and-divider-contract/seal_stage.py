"""Source recheck and stage210 registration; preserves16requirements and all grants."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess,tarfile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R));P=B/'stage209-current-GPIO-driver-and-link-timing'
PREV='6257090e81de5ab9e09e002af06e26f740fb4c8fdab908d6db3fa161f9fd0640';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        while chunk:=f.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,value):
    with (H/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==46
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
proof=json.loads((H/'early-link-and-time-proof.json').read_text());assert len(proof['selected_original_ranges'])==17 and len(proof['source_line_pins'])==7
for row in proof['selected_original_ranges']:
    p=R/row['source'];raw=p.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];base=int(row['base'],16);a,z=int(row['start'],16),int(row['end_exclusive'],16);part=raw[a-base:z-base]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
for row in proof['source_line_pins']:
    p=R/row['source'];raw=p.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];part=b''.join(raw.splitlines(keepends=True)[row['start_line']-1:row['end_line_inclusive']]);assert sha256(part).hexdigest()==row['sha256'] and part==(R/row['output']).read_bytes()
assert digest(R/proof['current_NOR']['config'])==proof['current_NOR']['config_sha256']
assert proof['current_NOR']['frame_bytes']==128 and not proof['current_NOR']['rate_input_initialization_or_current_value_proven']
t=proof['timing'];assert t['full84B_equal'] and t['startup_CNTFRQ_literal']==2000000 and t['divisor_at_declared_2MHz']==2 and t['input_x0_unused']
assert [t['setup_counter_delta_threshold'],t['hold_counter_delta_threshold']]==[101,1001] and t['baselines_precede_GPIO_edges'] and t['thresholds_are_not_actual_pin_pulse_widths']
assert not t['actual_Timer0_rate_or_PIN_timing_proven'] and not proof['SIO_parent_frequency_or_divider_formula_proven'] and not proof['current_early_rate3_or19_selected']
assert len(proof['kernel_SIO_descriptors'])==3 and all(r['clock_field_all_zero'] for r in proof['kernel_SIO_descriptors'])
assert digest(R/proof['source_symbol_catalog'])==proof['source_symbol_catalog_sha256']
cap=json.loads((H/'clock-source-capture.json').read_text());assert len(cap['files'])==9 and digest(R/cap['archive'])==cap['archive_sha256']=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
with tarfile.open(R/cap['archive'],'r:gz') as tf:
    for row in cap['files']:
        raw=(R/row['output']).read_bytes();assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'] and tf.extractfile(row['member']).read()==raw
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for name in ['configuration-writer-candidates.json','configuration-writer-literal-candidates.json']:
    c=json.loads((H/name).read_text());assert c['candidate_only'] and c['not_a_complete_control_flow_or_alias_proof']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert len(old['requirements'])==16 and native['goal']['status']=='active' and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='CURRENT_EARLY_SIO_AND_SHARED_COUNTER_CONTRACT_BOUND',previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Current NOR SIO transaction now reads rate atFE0625CC, channel/CS adjacent. Current/reference counter normalization84B are identical with2MHz startup declaration; input2 is unused, thresholds101/1001 start before GPIO edges. Current SIO resource clock fields zero do not identify parent. Next trace actual rate/config initialization and load-data sources, not guess Hz from empty descriptors.',
    limits=proof['limits'],root01='195 specific approval pending; no launch/job or repeated question',Sony_code_or_guest_execution=False,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_OFFLINE_EARLY_LINK_AND_TIME_BINDING',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=46,
    original_ranges_reverified=17,source_line_pins_reverified=7,GPL_clock_layout_members=9,current_reference_time_routine_equal_bytes=84,CNTFRQ_source_literal=2000000,
    counter_delta_thresholds=[101,1001],actual_GPIO_pulse_width_or_clock_Hz_proven=False,actual_early_rate_value_proven=False,SIO_parent_or_divider_formula_proven=False,
    current_SIO_descriptors_with_zero_clock_fields=3,host01_bundle_sha256_unchanged=HOST,host01_job_absent=True,release0_4_zip_unchanged=True,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Current NOR SIO transaction/config inputs and128B FIFO now source-bound. Shared current/reference84B counter routine usesCNTPCT/CNTFRQ;2MHz declaration,101/1001threshold baselines predate GPIO edges, no measured pulse widths.3current SIO clock descriptors zero; parent/rate initialization unresolved.17ranges/7source pins; no Sony/guest/root/device actions;195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('210绑当前NOR早期SIO事务和FE0625CC配置读点；当前/参考84B计时叶完全相同，CNTFRQ声明2MHz，101/1001基线早于GPIO，非脉宽。3当前SIO时钟字段全零不证父频率。17原范围/7源码行；下一项速率初始化/加载数据，无设备/root/guest，16要求和授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',contract=REL+'/early-link-and-time-proof.json',GPL_capture=REL+'/clock-source-capture.json',boundaries=REL+'/analysis-boundaries.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage210_early_SIO_clock_and_counter_contract']=ev
new['recovery_early_SIO_clock_and_counter_contract']={**ev,'current_NOR_transaction':'0xfe052348','current_NOR_rate_input':'0xfe0625cc','current_reference_counter84B_equal':True,'CNTFRQ_source_literal':2000000,
    'counter_thresholds_not_GPIO_pulse_widths':True,'SIO_parent_or_divider_formula_proven':False,'current_early_rate_input_initialized_value_proven':False,'actual_current_body_transport_or_boot_entry_proven':False,'same_body_backup_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准、不启动、不重问；主机试验不自动放行相机。',
    '沿当前NOR速率输入FE0625CC和通道/CS相邻字段，追实际初始化、加载数据及调用者；直接读点已绑，线性候选扫描未找到写者不证明不存在，不能先选择3或19。',
    '按CNTPCT/CNTFRQ源合同区分计数阈值与GPIO边沿脉宽，保留参考Timer0实际4MHz和SIO父时钟/分频待证；保留同机boot0/p1、独立AP入口、备份逆写/救砖及16要求和真实MAIN1080p29.97 HEVC长录验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib);marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3早期SIO与计时合同](<'+REL+'/README.md>)：当前事务/配置读点已绑，双方84B计时叶相同、CNTFRQ声明2MHz；101/1001非脉宽，SIO父频率/初始化未证。17原范围/7源码行；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage210-early-SIO-clock-and-counter-contract-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=46,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),source_ranges=17,source_line_pins=7,shared_time_routine_bytes=84,current_rate_value_proven=False,SIO_parent_Hz_proven=False,
    requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
