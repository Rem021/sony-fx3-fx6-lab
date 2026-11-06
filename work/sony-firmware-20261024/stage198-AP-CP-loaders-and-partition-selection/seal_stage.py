"""Seal source-only boot-component research; preserve all physical gates."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
from copy import deepcopy
import json, os, plistlib, re, stat, subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
P=B/'stage197-SPI-boot-mode-and-remote-boundary'
REL=str(H.relative_to(R));PSHA='562b428167086f1545dd244d23a570d099cc361ea69dbfcf5fd077a8f95dde11'
HSHA='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
SPI_SHA='314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
assert digest(P/'final-receipt.json')==PSHA
pm=json.loads((P/'final-receipt.json').read_text())
for e in pm['files']:
    p=R/e['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
assert len(pm['files'])==29
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HSHA
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
inv=json.loads((H/'source-inventory.json').read_text());hand=json.loads((H/'fixed-handoff-proof.json').read_text())
remaining=json.loads((H/'remaining-candidates.json').read_text())
for e in inv['sources']:
    p=Path(e['path']);assert p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
for e in inv['components']:
    p=Path(e['output']);assert p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
assert digest(Path(inv['reader_path']))==inv['reader_sha256']
assert digest(H/'originals/darwin_core.bin')==remaining['darwin']['sha256']
assert digest(Path(remaining['p5']['path']))==remaining['p5']['sha256_verified']
assert hand['source_sha256']==digest(H/'originals/loader_spi.bin')==SPI_SHA
assert hand['fixed_handoff_target']==hand['cpapp_b_config_load']=='0x108000'
assert hand['SPSR_EL3']=='0x13' and hand['x0_no_write_in_target_leaf']
assert not hand['p1_p3_selection_proven'] and not hand['original_or_guest_execution']
spi=(H/'originals/loader_spi.bin').read_bytes()
for e in hand['selected_original_ranges']:
    a,z=int(e['start_offset'],16),int(e['end_offset_exclusive'],16)
    assert len(spi[a:z])==e['bytes'] and sha256(spi[a:z]).hexdigest()==e['sha256']
assert len(hand['selected_original_ranges'])==4
darwin=json.loads((H/'darwin-mapping-candidates.json').read_text())
assert darwin['source_sha256']==remaining['darwin']['sha256']
assert len(darwin['candidates'])==2 and not any(e['mapping_validated'] for e in darwin['candidates'])
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link:assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert len(old['requirements'])==16 and native['goal']['status']=='active'
assert not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
review={
 'status':'SPI_FIXED_CP_ENTRY_VERIFIED_AP_RECOVERY_STILL_MISSING',
 'new_evidence':[
  'current7.02 p8 loader_spi.bin39184B extracted and source-hashed; four handoff slices bind fixed x0=0x108000 through relative branch/tail branch into ELR_EL3 and ERET',
  'SCR0x30/SPSR0x13 plus same-package cpapp-b load0x108000 support CP/TOPPERS-side handoff interpretation, not an AP p1/p3 recovery proof',
  'current7.02 DGU/MIS/tomco and full-FDAT darwin_core original captured as separate components; sender/controller identities unresolved',
  'historical2.05 p1 directory and AP load0x400080000 kept explicitly historical; currentp1/boot0 not obtained',
  'p5 original hash and WBI2 signature rechecked only; not promoted to a full parsed recovery image'],
 'limitations':[
  'SPI display VA tentative; source offsets, constants and relative branch checks are authoritative, no runtime PC claim',
  'ordinary return of preceding sequence/log/cache calls assumed; no whole-device path reachability or all callee effects proved',
  'no claim that whole loader_spi never participates in p1/p3 logic; the observed fixed handoff is insufficient to establish it',
  'Darwin tentative0/0x4000 mappings not established, not rejected for every possible transformed/runtime layout',
  'A7IV boot0 parser is an acquisition lead only, no FX3 key/format/payload compatibility inferred'],
 'pending_root01':'same195bundle, no specific reply, no job created, no administrator launch or repeated question',
 'original_or_guest_execution':False,'root_or_device_operations':0,
 'goal_complete':False,'persistent_write_release':False}
put('implementation-review.json',review)
put('verification-receipt.json',{
 'status':'PASS_SOURCE_BOUND_FIXED_HANDOFF_REVIEW','created_utc':now,
 'previous_manifest_sha256':PSHA,'previous_members_reverified':29,
 'SPI_source_sha256':SPI_SHA,'fixed_handoff_target':'0x108000',
 'matches_same_package_cpapp_config':True,'raw_instruction_handoff_verification':True,
 'selected_original_ranges':4,'newly_captured_original_components':7,
 'historical_p1_explicitly_separate':True,'Darwin_mapping_established':False,
 'new_runtime_or_guest_tests':0,'root_or_device_operations':0,
 'host01_bundle_sha256_unchanged':HSHA,'new_approval_granted':False})
new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=H.name
new['research_activity']='Current7.02 p8 SPI loader fixed handoff traced by source offsets/raw A64 fields to0x108000, matching same-package cpapp-b config and AArch32 SVC interpretation. Distinguish CP handoff from unproven AP p1/p3 recovery; capture DGU/MIS/tomco/Darwin source candidates and historical2.05 AP reference separately. No original/guest/device/root execution;195 consent still pending.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('198新提取7.02 SPI/DGU/MIS/tomco与Darwin原件并绑定来源；原始编码固定交接0x108000→ELR/ERET，匹配cpapp配置/SPSR0x13，更符合CP链，不充AP恢复。4原切片，旧2.05 AP地址分开；Darwin映射未证，p5仅WBI2签名。下一步追FX3 AP早期原件，不重复PWD。195待答，无设备/root/guest；16要求及全部授权不变。')
evidence={'readme':REL+'/README.md','verification':REL+'/verification-receipt.json','handoff':REL+'/fixed-handoff-proof.json','inventory':REL+'/source-inventory.json','remaining':REL+'/remaining-candidates.json','scope':REL+'/implementation-review.json','web_review':REL+'/web-source-review.json','original_or_guest_execution':False,'root_or_device_operations':0}
new['latest_stage_evidence']['stage198_SPI_CP_handoff_and_AP_boundary']=evidence
new['recovery_AP_CP_boot_component_boundary']={**evidence,'fixed_SPI_handoff_matches_CP_config':True,'current_AP_early_boot0_obtained':False,'p1_or_p3_selection_proven':False,'independent_restore_proven':False}
new['next_safe_offline_actions']=[
 '195 root01精确问题仍待用户回答；保持原bundle/未授权/固定作业未创建，不重复询问、不把继续视作批准。明确批准后才新开HOST_ONLY执行阶段。',
 '按198结果分开CP/TOPPERS固定交接和AP分区加载；优先查可取得的FX3 AP早期boot原件/公开资料，不能把A7IV boot0脚本的偏移、格式、密钥或payload自动视作FX3适配。',
 'Darwin电源/BOOT字符串仅定位候选，当前显示映射和SPI发送者未验；不据此生成硬件触发步骤。2.05 p1只作历史参考，当前同机p1、真实逆写、独立冷恢复和MAIN HD HEVC等全部16项仍保留。']
for k in ('authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial'):assert new[k]==old[k],k
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (H/'goal-status-after.json').open('xb') as f:f.write(after)
index=R/'README.md';ib=index.read_bytes()
with (H/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3 SPI固定交接与AP恢复边界](<'+REL+'/README.md>)：7.02另一加载器固定交接0x108000，与cpapp配置相符；DGU/MIS/Darwin原件已绑定来源，AP p1/p3入口和独立恢复仍未证；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (H/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS concurrent change'
for dest,content,name in ((canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')):
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',{'schema':'fx3-stage198-fixed-SPI-handoff-v1','created_utc':now,
 'previous_manifest_sha256':PSHA,'previous_members_reverified':29,'files':members,'member_count':len(members),
 'mutable_heads_not_manifest_members':True,'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(after).hexdigest(),
 'host01_bundle_sha256_unchanged':HSHA,'new_approval_granted':False,'original_or_guest_execution':False,'root_or_device_operations':0,
 'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'sealed_manifest_sha256':digest(H/'final-receipt.json'),'members':len(members),'requirements_unchanged':16,'all_authorizations_unchanged':True,'root_or_device_operations':0,'goal_complete':False}))
