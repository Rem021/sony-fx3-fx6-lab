"""Preserve a bounded plan decision and update progress without device work."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,copy,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/'final-receipt.json').exists()
def sha(raw):return sha256(raw).hexdigest()
def enc(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def save(name,raw):
 with (H/name).open('xb') as f:f.write(raw)
prev=B/'stage244-highcapacity-session-admission';raw=(prev/'final-receipt.json').read_bytes()
assert sha(raw)=='eedeff9d32a648ab3beb14f0a833bafc4b1ca1e419757e109a574bf4f2e8a111'
seal=json.loads(raw)
for rec in seal['files']:
 data=(R/rec['path']).read_bytes();assert len(data)==rec['bytes'] and sha(data)==rec['sha256']
plan=json.loads((H/'probe-plan.json').read_text());decision=json.loads((H/'decision.json').read_text())
assert len(plan['proposed_operations'])==4 and not plan['executable_or_approved']
assert decision['status']=='REJECT_NO_MODE_CHANGE_MINIMAL_SENSER_PROPOSAL'
gpath=B/'GOAL_STATUS.json';gb=gpath.read_bytes();goal=json.loads(gb)
assert gb==(prev/'goal-status-after.json').read_bytes()
protected=('authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority')
saved={k:copy.deepcopy(goal[k]) for k in protected};assert len(goal['requirements'])==16
assert goal['goal_manager_status']=='cleared_by_user' and not goal['persistent_write_release']
root=R/'README.md';rb=root.read_bytes();road=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=road.read_bytes()
assert rb==(prev/'readme-after.md').read_bytes() and mb==(prev/'roadmap-after.md').read_bytes()
text=rb.decode();overview=next(x for x in text.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3最小通信诊断与准入结论](<work/sony-firmware-20261024/stage245-minimal-communication-admission/README.md>)：固定4操作评审候选，START/STOP原控制头与停止其它驱动/事件路径对应，不满足不切状态保证；本路线停止同输入离线追加。195仅主机实测仍未执行，第2项未完成，无设备操作。'
ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
text=mb.decode().replace('最新研究证据为第244阶段。','最新研究证据为第245阶段。',1)
old='最新判定：原厂类别与接收端静态连接已核对；现有GET_FILE2回传路线保持不放行。尚未形成可执行真机诊断，本批无需接线。[具体依据](../../work/sony-firmware-20261024/stage244-highcapacity-session-admission/README.md)。'
new='最新判定：4操作最小通信候选已评审；START/STOP可能影响其它USB驱动和事件状态，不能满足不切状态保证，因此尚不可执行，相机无需连接。仅主机跨用户身份/受保护回执仍未实测；同一输入不再追加这条方案的离线模型。[具体判定和前置](../../work/sony-firmware-20261024/stage245-minimal-communication-admission/README.md)。'
assert old in text;ma=text.replace(old,new,1).encode()
now=datetime.now(timezone.utc).isoformat();goal['updated_utc']=now;goal['latest_stage']=H.name
goal['recovery_minimal_communication_admission']={
 'readme':str((H/'README.md').relative_to(R)),'plan':str((H/'probe-plan.json').relative_to(R)),
 'decision':str((H/'decision.json').relative_to(R)),'milestone':2,'milestone_complete':False,
 'candidate_operations':4,'executable':False,'camera_needed_for_this_batch':False,
 'no_mode_or_driver_state_change_contract_rejected':True,
 'old_static_findings_reused_for_admission_not_new_hardware_progress':True,
 'no_more_same_input_offline_models':True,'host195_remains_unapproved_unexecuted':True,
 'new_device_USB_cache_admin_auth_or_firmware_operations':0}
goal['next_safe_offline_actions']=[
 '245已交付4操作最小通信方案及不切状态合同的否决；对相同输入停止新增模型/包装器/重复审查，不把START/STOP报错或省略认证摘要解释为无副作用。',
 '当前实际前置是仅主机跨UID和受保护回执实测；195固定方案保留未批准未执行，本批不重新申请/不启动。只有新的明确操作授权或不同的可信主机证据才推进这一实测，不因用户要求继续研究而执行管理员程序。',
 '之后的相机方案须明确USB驱动/会话潜在变化、固定程序和单次操作边界，并验证真实退出归还；当前没有上机入口。G01至G16、恢复优先和0.4/0.5及23源码不变，首刷前2至6共5项未完成，自动目标不重建。']
goal['current_native_goal_observation']={
 'receipt':str((H/'native-goal-observed.json').relative_to(R)),'observed_utc':now,'status':'none',
 'source':'native get_goal read only','user_cleared_goal':True,
 'research_continued_by_direct_user_request':True,'goal_recreated':False,'device_authorization_expanded':False}
goal['goal_complete']=False;goal['persistent_write_release']=False
assert {k:goal[k] for k in protected}==saved;ga=enc(goal)
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),
 ('readme-before.md',rb),('readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma),
 ('native-goal-observed.json',enc({'goal':None,'observed_utc':now,'recreated':False})),
 ('public-source-review.json',enc({'reviewed_utc':now,'source':'https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py',
 'reference':'StartSenser/StopSenser and command1 challenge request; source read as text/AST only',
 'FX3_driver_state_claim_source':'saved official library and kernel module; not inferred from PMCA alone'}))]:save(name,data)
assert gpath.read_bytes()==gb and root.read_bytes()==rb and road.read_bytes()==mb
gpath.write_bytes(ga);root.write_bytes(ra);road.write_bytes(ma)
assert gpath.read_bytes()==ga and root.read_bytes()==ra and road.read_bytes()==ma
receipt=dict(created_utc=now,status=decision['status'],milestone=2,milestone_complete=False,
 candidate_plan_operations=4,executable_or_approved=False,
 prior_stage_members_reverified=len(seal['files']),new_model_tests=0,previous_model_tests_repeated=0,
 new_camera_USB_cache_admin_auth_or_firmware_operations=0,
 original_Sony_Linux_glibc_or_downloaded_camera_code_executed=False,
 root195_not_executed_or_requested=True,formal_tools_changed=False,requirements16_and_authorizations_unchanged=True,
 automatic_goal_recreated=False,goal_complete=False,persistent_write_release=False,
 live_head_sha256={'goal':sha(ga),'root_readme':sha(ra),'roadmap':sha(ma)})
save('verification-receipt.json',enc(receipt))
members=[]
for p in sorted(H.rglob('*')):
 if p.is_file():
  data=p.read_bytes();members.append(dict(path=str(p.relative_to(R)),bytes=len(data),sha256=sha(data)))
save('final-receipt.json',enc(dict(schema='fx3-stage245-minimal-probe-admission-v1',
 previous_manifest_sha256=sha(raw),files=members,member_count=len(members),mutable_heads_not_manifest_members=True,**receipt)))
print(json.dumps(dict(status=decision['status'],members=len(members),manifest_sha256=sha((H/'final-receipt.json').read_bytes()),new_camera_operations=0)))
