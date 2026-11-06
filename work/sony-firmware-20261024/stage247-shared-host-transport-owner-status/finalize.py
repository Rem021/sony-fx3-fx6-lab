"""Seal the scoped offline integration and cache observation; launch nothing."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,copy,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/'final-receipt.json').exists()
def sha(raw):return sha256(raw).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def save(name,data):
 if not isinstance(data,bytes):data=enc(data)
 with (H/name).open('xb') as f:f.write(data)
prev=B/'stage246-authorized-host-root01';pm=(prev/'final-receipt.json').read_bytes()
assert sha(pm)=='d4407b6de7f6d4ac96ebfdd7706bc6c04a4e575a5d50b1a88d01ee298f060a68'
ps=json.loads(pm)
for x in ps['files']:
 raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha(raw)==x['sha256']
review=json.loads((H/'integration-review.json').read_text());cache=json.loads((H/'current-cache-target.json').read_text())
assert review['changed_integration_checks']==8 and review['current_location_smoke_checks']==2
assert cache['candidate_count']==1 and cache['candidates'][0]['locationID']==0x01100000
build=json.loads((H/'build-receipt-current-port.json').read_text())
for x in build['sources']:assert sha((H/x['path']).read_bytes())==x['sha256']
for x in build['builds'].values():assert sha(Path(x['path']).read_bytes())==x['sha256']
assert '#define FX3_NATIVE_RELEASED 0' in (H/'entry_target.h').read_text()
gpath=B/'GOAL_STATUS.json';gb=gpath.read_bytes();assert gb==(prev/'goal-status-after.json').read_bytes()
g=json.loads(gb);protected_names=('authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority','authorization_consumption')
protected={k:copy.deepcopy(g[k]) for k in protected_names}
assert g['authorization']['Mac_cached_USB_metadata_authorized'] is True
assert g['authorization_consumption']['Mac_root_host01']['consumed'] is True
now=datetime.now(timezone.utc).isoformat()
save('cache-connection-receipt.json',dict(user_response='已连接Mac，保持MSC',
 scope='previously authorized Mac cached USB metadata only',queries=1,
 camera_interface_opened_or_media_read_or_Sony_commands=False,
 sanitized_source=str((H/'current-cache-target.json').relative_to(R))))
g['updated_utc']=now;g['latest_stage']=H.name
g['recovery_shared_host_transport_owner_status']={
 'readme':str((H/'README.md').relative_to(R)),
 'review':str((H/'integration-review.json').relative_to(R)),
 'current_build':str((H/'build-receipt-current-port.json').relative_to(R)),
 'diagnostic_draft':str((H/'diagnostic-plan.json').relative_to(R)),
 'integration_checks':8,'current_port_smoke_checks':2,'native_released':False,'native_executed':False,
 'root195_transport_component_source_adopted':True,'new_integrated_root_cross_UID_acceptance':False,
 'cache_queries':1,'current_port':'0x01100000','same_unit_tag_materialized':False,
 'new_admin_or_camera_commands':0,'milestone2_complete':False}
g['current_native_owner_channel_candidate'].update(
 readme=str((H/'README.md').relative_to(R)),build=str((H/'build-receipt-current-port.json').relative_to(R)),
 verification=str((H/'integration-review.json').relative_to(R)),
 identifier='fx3-702-owner-status-20261030-11',explicitly_approved=False,
 native_authentication_scope_released=False,native_frame_and_supervisor_factory_ready=False,
 root_HOST_ONLY_component_actual_validated=True,new_integrated_native_executed=False,
 allowed_control_ops=['OBSERVE','STATUS','END'],current_cached_location='0x01100000')
g['current_Mac_cache_observation']={
 'receipt':str((H/'current-cache-target.json').relative_to(R)),
 'user_reports_mode':'MSC','VID':'054C','PID':'0DA1','location':'0x01100000',
 'unique_root_cache_candidate':True,'serial_values_selected_used_or_saved':False,
 'same_unit_firmware_or_active_USB_health_proven':False}
g['next_safe_offline_actions']=[
 '第2里程碑继续实现247原生数据页准备与root监督器工厂，当前工厂拒绝执行、native标志仍0；不得用195已消耗授权启动新程序。',
 '将夹具机身标签换成明确同机材料并把当前缓存目标准入接到运行检查。247一次缓存定位唯一054C:0DA1/0x01100000；不把缓存节点号或端口常量当机身固件哈希或USB归还证明。',
 '固定新单次构建/nonce/操作范围/批准包后，才请求具体管理员与USB接管归还试验。该候选只OBSERVE/STATUS/END、不发Sony命令；244/245路线不放行，原16项与恢复优先保持，首刷前2至6共5项未通过，自动目标不重建。']
g['current_native_goal_observation']={
 'receipt':str((H/'native-goal-observed.json').relative_to(R)),'observed_utc':now,
 'status':'none','source':'native get_goal read only','user_cleared_goal':True,
 'research_continued_by_direct_user_request':True,'goal_recreated':False,'device_authorization_expanded':False}
g['goal_complete']=False;g['persistent_write_release']=False
assert {k:g[k] for k in protected_names}==protected;ga=enc(g)
root=R/'README.md';rb=root.read_bytes();text=rb.decode()
overview=next(x for x in text.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3主机回执与状态控制端整合](<work/sony-firmware-20261024/stage247-shared-host-transport-owner-status/README.md>)：复用246实测的主机传输代码，状态控制端8项整合/2项当前端口进程检查通过；一次授权缓存识别唯一FX3，端口适配0x01100000。原生工厂/同机绑定/单次包未就绪，入口关闭，无新管理员/相机命令。'
assert H.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
road=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=road.read_bytes();text=mb.decode()
assert '最新研究证据为第246阶段。' in text;text=text.replace('最新研究证据为第246阶段。','最新研究证据为第247阶段。',1)
old='最新实测：Mac仅主机root身份、自读握手、受保护归档、新nonce回读与原进程退出已通过；两次helper已结束，本次授权已消耗。第2项整体仍未完成，当前不需要连接相机。[实际回执](../../work/sony-firmware-20261024/stage246-authorized-host-root01/README.md)。'
new='最新进展：246仅主机实测代码已接入状态控制端，8项整合检查与2项端口检查通过。用户连接后一次缓存识别唯一FX3、当前端口0x01100000；未打开相机接口。原生启动器、同机绑定材料和新单次执行包仍未就绪，第2项未完成。[代码与缓存结果](../../work/sony-firmware-20261024/stage247-shared-host-transport-owner-status/README.md)。'
assert old in text;text=text.replace(old,new,1)
old='进行中；Mac仅主机跨用户身份与受保护回执实测通过；真机通信、自写程序执行及可信回传未通过'
new='进行中；主机实测及状态控制端整合通过，当前缓存端口已定位；原生启动/同机绑定/单次包及真机验收未完成'
assert old in text;text=text.replace(old,new,1)
old='只推进第2项：先离线整合已实测的主机身份/回执与原生MSC拥有者，保持原生入口关闭，核对端点、作用域、在途调用和驱动归还。新管理员或USB动作需要新的具体范围与授权；195单次试验已完成，不再重复。只有针对新改动或实际失败才增加必要验证。'
new='只推进第2项：接通原生数据页与root监督器工厂，落实同机绑定和当前目标运行准入，再固定新单次包。状态控制端整合已通过，不重复旧套件；当前入口仍关闭。新管理员与USB接管/归还须有具体范围与授权，195单次试验已用完。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before.json',gb),('goal-status-after.json',ga),('readme-before.md',rb),
 ('readme-after.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma),
 ('native-goal-observed.json',enc(dict(goal=None,observed_utc=now,recreated=False)))]:save(name,data)
assert gpath.read_bytes()==gb and root.read_bytes()==rb and road.read_bytes()==mb
gpath.write_bytes(ga);root.write_bytes(ra);road.write_bytes(ma)
assert gpath.read_bytes()==ga and root.read_bytes()==ra and road.read_bytes()==ma
receipt=dict(created_utc=now,status=review['status'],previous_manifest_sha256=sha(pm),
 previous_members_reverified=len(ps['files']),changed_integration_checks=8,current_port_checks=2,
 cached_metadata_queries=1,current_port='0x01100000',new_root_helper_invocations=0,
 camera_interface_opens_Sony_auth_or_commands_driver_capture_or_firmware_writes=0,
 original_Sony_Linux_glibc_or_downloaded_camera_code_executed=False,
 own_fixture_execution_only=True,native_executed=False,native_released=False,
 native_frame_factory_and_target_material_ready=False,milestone2_complete=False,
 all16_requirements_authorizations_and_prior_host_grant_consumption_unchanged=True,
 automatic_goal_recreated=False,goal_complete=False,persistent_write_release=False,
 live_head_sha256={'goal':sha(ga),'root_readme':sha(ra),'roadmap':sha(ma)})
save('verification-receipt.json',receipt)
files=[]
for p in sorted(H.rglob('*')):
 if p.is_file():
  raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha(raw)))
save('final-receipt.json',dict(schema='fx3-stage247-shared-transport-status-owner-v1',files=files,
 member_count=len(files),mutable_heads_not_manifest_members=True,**receipt))
print(json.dumps(dict(status=review['status'],members=len(files),manifest_sha256=sha((H/'final-receipt.json').read_bytes()),cache_queries=1,new_admin_or_camera_commands=0)))
