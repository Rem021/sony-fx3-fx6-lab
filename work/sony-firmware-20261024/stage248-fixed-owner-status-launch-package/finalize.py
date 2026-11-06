"""Seal an unapproved fixed owner-status package; never stage or execute it."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,copy,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/'final-receipt.json').exists()
def sha(b):return sha256(b).hexdigest()
def enc(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def save(name,data):
 if not isinstance(data,bytes):data=enc(data)
 with (H/name).open('xb') as f:f.write(data)
prev=B/'stage247-shared-host-transport-owner-status';pm=(prev/'final-receipt.json').read_bytes()
assert sha(pm)=='c2d5e059c3071aeae2b28354895a0b848c10424fb43d3dde0ac062e7172d75f1'
ps=json.loads(pm)
for row in ps['files']:
 data=(R/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
br=(H/'approval-bundle.json').read_bytes();digest=sha(br)
assert digest=='c372c53f14b746ad9e9f04ad50c94af5890a7320dccf73ff354179eed0bcff41'
bundle=json.loads(br)
for row in bundle['files']:
 data=(H/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
tests=json.loads((H/'package-test-receipt.json').read_text());assert tests['checks']==8
assert tests['new_root_helper_or_USB_operations']==0 and tests['live_cache_queries']==0
assert not Path('/private/tmp/fx3-702-owner-status-20261030-11').exists()
gpath=B/'GOAL_STATUS.json';gb=gpath.read_bytes();assert gb==(prev/'goal-status-after.json').read_bytes()
g=json.loads(gb);names=('authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority','authorization_consumption')
protected={k:copy.deepcopy(g[k]) for k in names};assert len(g['requirements'])==16
assert 'Mac_owner_status11' not in g['authorization']
now=datetime.now(timezone.utc).isoformat();plan=json.loads((H/'fixed-plan.json').read_text())
g['updated_utc']=now;g['latest_stage']=H.name
g['prepared_owner_status11_trial']={
 'readme':str((H/'README.md').relative_to(R)),
 'fixed_plan':str((H/'fixed-plan.json').relative_to(R)),
 'bundle':str((H/'approval-bundle.json').relative_to(R)),'bundle_sha256':digest,
 'grant_id':plan['grant_id'],'scope':'MSC_OWNER_STATUS_ONLY','maximum_helper_invocations':1,
 'ready_for_new_specific_approval':True,'explicitly_authorized':False,'staged':False,'executed':False,
 'factory_native_frame_and_runtime_target_binding_implemented':True,
 'requires_fixed_root_private_permit':True,'general_native_release_flag':0,
 'target':plan['target'],'host_control_ops':plan['host_control_ops'],
 'actual_new_root_or_camera_acceptance':False,'Sony_auth_file_firmware_or_flash_released':False,
 'helper_sha256':plan['helper_sha256'],'old195_authorization_not_accepted':True}
g['recovery_fixed_owner_status_package']={
 'readme':str((H/'README.md').relative_to(R)),'offline_checks':8,
 'permit_file_cases':5,'permit_field_and_registry_checks':17,
 'native_frame_factory_completed':True,'runtime_cached_node_admission_completed':True,
 'same_unit_consistency_tag_generated_only_in_approved_root_helper':True,
 'new_integrated_root_or_camera_executed':False,'live_cache_queries_this_stage':0,
 'milestone2_complete':False,'ready_for_specific_diagnostic_approval_only':True}
g['current_native_owner_channel_candidate'].update(
 readme=str((H/'README.md').relative_to(R)),build=str((H/'build-receipt.json').relative_to(R)),
 verification=str((H/'package-test-receipt.json').relative_to(R)),
 identifier=plan['grant_id'],explicitly_approved=False,
 native_frame_and_supervisor_factory_ready=True,fixed_target_admission_code_ready=True,
 fixed_root_private_status_permit_ready=True,new_integrated_native_executed=False,
 native_authentication_scope_released=False,ready_for_specific_status_diagnostic_approval=True)
g['next_safe_offline_actions']=[
 '248已补齐原生帧/root监督器工厂、接管前缓存目标准入及root私有单次许可，并固定50文件批准包c372c53f14b746ad9e9f04ad50c94af5890a7320dccf73ff354179eed0bcff41；不再为这三项追加同类模型。',
 '下一步仅在用户明确批准本新MSC_OWNER_STATUS_ONLY范围、手动推出所有相机卷并保持原端口/MSC后，执行一次限定接管/归还诊断；最多一个root helper，无Sony认证/模式/文件/固件命令。195已消耗授权不能复用；当前不启动。',
 '执行前工厂再次核对缓存节点，变化即在作业创建前拒绝，不自动改端口/重试。原生helper以缓存序列号HMAC作一致性标签、无原序列号落盘；不代表固件认证。真实驱动归还/相机观察与G01至G16仍待验，不能首刷，自动目标不重建。']
g['current_native_goal_observation']={
 'receipt':str((H/'native-goal-observed.json').relative_to(R)),'observed_utc':now,
 'status':'none','source':'native get_goal read only','user_cleared_goal':True,
 'research_continued_by_direct_user_request':True,'goal_recreated':False,'device_authorization_expanded':False}
g['goal_complete']=False;g['persistent_write_release']=False
assert {k:g[k] for k in names}==protected;ga=enc(g)
root=R/'README.md';rb=root.read_bytes();text=rb.decode()
overview=next(x for x in text.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3单次USB接管与归还诊断固定方案](<work/sony-firmware-20261024/stage248-fixed-owner-status-launch-package/README.md>)：原生帧/监督器、接管前缓存节点与私有HMAC绑定、root单次许可已接通；8项离线核验通过，50文件包c372c53f固定。仅状态控制，待新单次管理员与USB接管批准；未暂存/启动，无新缓存或设备操作，仍不能首刷。'
assert H.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
road=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=road.read_bytes();text=mb.decode()
assert '最新研究证据为第247阶段。' in text;text=text.replace('最新研究证据为第247阶段。','最新研究证据为第248阶段。',1)
old='最新进展：246仅主机实测代码已接入状态控制端，8项整合检查与2项端口检查通过。用户连接后一次缓存识别唯一FX3、当前端口0x01100000；未打开相机接口。原生启动器、同机绑定材料和新单次执行包仍未就绪，第2项未完成。[代码与缓存结果](../../work/sony-firmware-20261024/stage247-shared-host-transport-owner-status/README.md)。'
new='最新进展：原生启动器、接管前目标准入/运行时一致性标签和新单次执行包已补齐，50文件构建已固定并通过离线核验。下一步是新范围的一次真机接管与归还诊断，需单独批准并手动推出相机全部卷；当前尚未启动，第2项实机验收未完成。[固定诊断方案](../../work/sony-firmware-20261024/stage248-fixed-owner-status-launch-package/README.md)。'
assert old in text;text=text.replace(old,new,1)
old='进行中；主机实测及状态控制端整合通过，当前缓存端口已定位；原生启动/同机绑定/单次包及真机验收未完成'
new='进行中；主机实测和代码整合通过，原生启动/目标绑定/单次包已准备；新接管归还诊断待批准与实机验收'
assert old in text;text=text.replace(old,new,1)
old='只推进第2项：接通原生数据页与root监督器工厂，落实同机绑定和当前目标运行准入，再固定新单次包。状态控制端整合已通过，不重复旧套件；当前入口仍关闭。新管理员与USB接管/归还须有具体范围与授权，195单次试验已用完。'
new='第2项下一步执行248固定的单次接管/归还诊断，须先取得新范围批准并由用户手动推出全部相机卷。未批准时保留包，不再追加同类模型；执行中不自动重试/强杀/重置，无法确认时保留UNKNOWN。195授权已用完，不覆盖本方案。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('readme-before.md',rb),('readme-after.md',ra),
 ('roadmap-before.md',mb),('roadmap-after.md',ma),('native-goal-observed.json',enc(dict(goal=None,observed_utc=now,recreated=False)))]:save(name,data)
assert gpath.read_bytes()==gb and root.read_bytes()==rb and road.read_bytes()==mb
gpath.write_bytes(ga);root.write_bytes(ra);road.write_bytes(ma)
assert gpath.read_bytes()==ga and root.read_bytes()==ra and road.read_bytes()==ma
receipt=dict(created_utc=now,status='FIXED_STATUS_ONLY_DIAGNOSTIC_PACKAGE_PREPARED_NOT_APPROVED_OR_EXECUTED',
 previous_manifest_sha256=sha(pm),previous_members_reverified=len(ps['files']),
 approval_bundle_sha256=digest,approval_members=50,offline_checks=8,permit_file_cases=5,
 native_factory_frame_and_target_binding_implemented=True,root_private_fixed_permit_required=True,
 scope='MSC_OWNER_STATUS_ONLY',maximum_helper_invocations=1,explicitly_approved=False,
 native_job_staged=False,native_helper_executed=False,live_cache_queries=0,
 new_admin_USB_driver_auth_or_firmware_operations=0,all16_requirements_and_authorizations_unchanged=True,
 automated_goal_recreated=False,goal_complete=False,persistent_write_release=False,
 live_head_sha256={'goal':sha(ga),'root_readme':sha(ra),'roadmap':sha(ma)})
save('verification-receipt.json',receipt)
files=[]
for p in sorted(H.rglob('*')):
 if p.is_file():
  raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha(raw)))
save('final-receipt.json',dict(schema='fx3-stage248-fixed-status-diagnostic-v1',files=files,member_count=len(files),mutable_heads_not_manifest_members=True,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(files),manifest_sha256=sha((H/'final-receipt.json').read_bytes()),approval_bundle_sha256=digest,executed=False)))
