"""Seal current source-only MCU findings without expanding any authorization."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
P=B/'stage198-AP-CP-loaders-and-partition-selection';REL=str(H.relative_to(R))
PSHA='9bc31adca65bd9d5e18daa7f5e064f0ebddcce889342b5239977969c55359d86'
DSHA='ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
HSHA='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
assert digest(P/'final-receipt.json')==PSHA
prior=json.loads((P/'final-receipt.json').read_text())
for e in prior['files']:
    p=R/e['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
assert len(prior['files'])==38
src=P/'originals/darwin_core.bin';assert digest(src)==DSHA;data=src.read_bytes()
v=json.loads((H/'vector-source-proof.json').read_text());u=json.loads((H/'update-control-proof.json').read_text());i=json.loads((H/'InitCom-link-proof.json').read_text())
assert v['source_sha256']==u['source_sha256']==i['source_sha256']==DSHA
assert v['source_layout_base']==u['source_layout_base']==i['source_layout_base']=='0x4200'
selected=v['selected_ranges']+u['selected_ranges']+i['selected_ranges'];assert len(selected)==19
for e in selected:
    a,z=int(e['start'],16)-0x4200,int(e['end_exclusive'],16)-0x4200
    assert z-a==e['bytes'] and sha256(data[a:z]).hexdigest()==e['sha256']
assert v['raw_BL_target']=='0x4674' and v['runtime_branch_pointer']=='0x43fd'
assert u['Seton_conditional_route']['selected_next_state']==5
assert u['Seton_conditional_route']['next_table_for_these_values']==[2,3,5]
assert u['Upd_transfer']['vector_argument']==0 and not u['Upd_transfer']['bootloader_original_bytes_obtained']
assert i['local_producer_for_Seton_halfwords_identified_conditionally']
assert i['conditional_local_producer']['after_return0_and_output4']['packed_word']=='0x00040000'
assert not i['conditional_local_producer']['SVC_queue_implementation_or_delivery_verified']
coverage=json.loads((H/'darwin-package-coverage.json').read_text())
assert digest(Path(coverage['audit_path']))==coverage['audit_sha256']
assert digest(Path(coverage['darwin_sum_path']))==coverage['darwin_sum_sha256']
assert len(coverage['Darwin_named_payload_members'])==1
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HSHA
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link:assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert native['goal']['status']=='active' and len(old['requirements'])==16
assert not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('analysis-corrections.json',{
 'scope':'unsealed static analysis only; no native/guest/device retries',
 'corrections':[
  {'initial_check':'runtime slice ended0x442c','rejection':'cut a32bit Thumb instruction','corrected_end':'0x4430'},
  {'initial_check':'expected CBZ word mistakenly transcribed0xb918','observed_original':'0xb118','action':'corrected expected value; independent CBZ target field confirms0x879c'}],
 'invalid_proofs_accepted':False,'source_modified':False,'root_or_device_operations':0})
put('implementation-review.json',{
 'status':'FX3_DARWIN_CONDITIONAL_UPDATE_ROUTE_LOCATED_NOT_AP_RECOVERY',
 'new_facts':[
  'source-map0x4200 coherent with distinct FX3 reset/fault vectors, raw BL4674 and pool/BX43fd',
  'original InitCom selected Cmd11/sub4 arm returns0/output4 after successful internal receive and matching CRC',
  'local producer conditionally constructs [0,4] for SVC11/selector0; Seton consumer returns2 and next table selects state5',
  'Upd-main writes MCU request4/zero then vector argument0 loads MSP/PSP from0 and PC from4, outside current core source map'],
 'critical_limits':[
  'ordinary ABI returns and callee-saved state assumed, selected paths only, no Sony/guest execution',
  'SVC delivery, whole-device reachability and external sender/physical SIO still unresolved',
  'Darwin vector target is distinct from AP eMMC boot0 and CP fixed handoff; no p1/p3/USB/Fastboot/independent rescue proof',
  'corrupt-core fallback, same-body currentp1/boot0, actual inverse write and MAIN HD HEVC recording unverified',
  'A6000 incident is a source-reported failure with open cause/recovery, not an FX3 diagnosis or ready recovery method'],
 'pending_root01':'same195 bundle; no specific response, fixed job absent, no launch or repeated question',
 'selected_source_slices':19,'original_or_guest_execution':False,'root_or_device_operations':0,
 'goal_complete':False,'persistent_write_release':False})
put('verification-receipt.json',{
 'status':'PASS_SOURCE_BOUND_DARWIN_CONDITIONAL_ROUTE_REVIEW','created_utc':now,
 'previous_manifest_sha256':PSHA,'previous_members_reverified':38,
 'source_sha256':DSHA,'source_layout_map':'0x4200','selected_original_slices':19,
 'raw_Thumb_reset_branch_pool_and_selected_control_checks':True,
 'SVC_delivery_or_external_entry_proven':False,'AP_independent_restore_proven':False,
 'original_or_guest_executions':0,'root_or_device_operations':0,
 'host01_bundle_sha256_unchanged':HSHA,'new_approval_granted':False})
new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=H.name
new['research_activity']='Distinct FX3 Darwin source now has coherent0x4200 reset/fault map verified by raw Thumb BL/pool fields. Selected Cmd11/sub4 InitCom arm links conditionally through local SVC argument producer and Seton result2/table state5 to Upd-main MCU vector transfer at0/4. No SVC delivery/external sender/corrupt-core/AP p1 rescue proof;19source slices, no original/guest/root/device execution.195 consent remains pending.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('199从社区基址线索回到FX3原字节：0x4200映射复位/异常向量自洽，raw Thumb BL/pool核对。InitCom Cmd11/sub4选中路径→本地SVC参数[0,4]→Seton结果2/next状态5→Upd-main向量0/4，19原切片。SVC交付/发送者/坏核心入口/AP恢复仍未证；A6000新失败报告仅作经验。195待答，无root/设备/guest，16要求与授权保持。')
evidence={'readme':REL+'/README.md','verification':REL+'/verification-receipt.json','vectors':REL+'/vector-source-proof.json','consumer':REL+'/update-control-proof.json','producer':REL+'/InitCom-link-proof.json','coverage':REL+'/darwin-package-coverage.json','scope':REL+'/implementation-review.json','web_review':REL+'/web-source-review.json','original_or_guest_execution':False,'root_or_device_operations':0}
new['latest_stage_evidence']['stage199_Darwin_source_map_and_conditional_update']=evidence
new['recovery_Darwin_conditional_update_route']={**evidence,'source_layout_map':'0x4200','conditional_local_input_producer_located':True,'SVC_delivery_proven':False,'external_sender_identified':False,'corrupt_core_fallback_proven':False,'AP_p1_or_p3_selection_proven':False,'independent_restore_proven':False}
new['next_safe_offline_actions']=[
 '195 root01具体问题仍待答；保持原bundle和未授权状态，不把继续/目标续行为批准，不创建固定作业或启动管理员，不重复询问。',
 '追199当前InitCom内部SIO的另一端发送者与官方Darwin初始化工具依赖；局部SVC参数生产者已找到，不能再当缺件，但SVC实际交付和坏核心入口未验。不要将Darwin向量0/4与AP eMMC boot0/CP入口混同。',
 '继续查可取得的FX3 AP早期选择原件和同机恢复所需来源；Darwin自身更新不替代p1/p3救援。保留当前p1/boot0、真实逆写与MAIN HD HEVC等全部16项验收。']
for k in ('authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial'):assert new[k]==old[k],k
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (H/'goal-status-after.json').open('xb') as f:f.write(after)
index=R/'README.md';ib=index.read_bytes()
with (H/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3 Darwin向量与条件更新回跳](<'+REL+'/README.md>)：0x4200源映射及Cmd11/sub4→本地参数→Seton/Upd向量0/4已静态连通；19原切片，SVC交付/坏核心及AP恢复未验；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (H/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name in ((canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')):
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',{'schema':'fx3-stage199-Darwin-source-route-v1','created_utc':now,'previous_manifest_sha256':PSHA,'previous_members_reverified':38,'files':members,'member_count':len(members),'mutable_heads_not_manifest_members':True,'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(after).hexdigest(),'host01_bundle_sha256_unchanged':HSHA,'new_approval_granted':False,'original_or_guest_execution':False,'root_or_device_operations':0,'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'sealed_manifest_sha256':digest(H/'final-receipt.json'),'members':len(members),'requirements_unchanged':16,'all_authorizations_unchanged':True,'root_or_device_operations':0,'goal_complete':False}))
