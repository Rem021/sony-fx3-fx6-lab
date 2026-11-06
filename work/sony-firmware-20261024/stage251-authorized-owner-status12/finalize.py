"""Seal actual status12 evidence. No root, USB call, cache query or new trial."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,plistlib,subprocess

D=Path(__file__).resolve().parent;B=D.parent;R=B.parents[1];H=B/'stage250-corrected-owner-status12-package'
assert not (D/'final-receipt.json').exists()
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,data):
    data=data if isinstance(data,bytes) else enc(data)
    fd=os.open(D/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data)
previous=json.loads((H/'final-receipt.json').read_text())
for x in previous['files']:
    raw=(R/x['path']).read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256'],x['path']
assert sha256((H/'approval-bundle.json').read_bytes()).hexdigest()=='57dc8a85d05360e5df098a75ace9fa422dd31293396c65bb238d2eec5a6a5910'
obs=json.loads((D/'actual-observation.json').read_text());private=json.loads((D/'private-record.json').read_text());live=json.loads((D/'live-final-summary.json').read_text());cache=json.loads((D/'post-trial-cache.json').read_text())
assert obs['original_helper_absent'] and obs['original_observer_absent'] and obs['post_cached_identity_and_MSC_match']
assert live['status']=='HOST_RETURN_OBSERVED' and live['helper_terminal_observed'] and private['transport_peer_verified']
assert (D/'received-final-record.bin').read_bytes()==(D/'private-record.bin').read_bytes()
assert sha256((D/'private-record.bin').read_bytes()).hexdigest()=='de47d6c9c73aa97c5150a01d6a7acf2ddfbd1b3028116f96f06c7850628b1b55'
assert not private['result']['cleanup_error'] and not private['result']['vendor_attempted'] and not private['result']['active_call_pending']
now=datetime.now(timezone.utc).isoformat()
put('user-validation-and-screen-confirmation.json',dict(observed_utc=now,user_native_validation_reply='已完成12号原生验证',user_screen_reply='正常显示USB／MSC，无报错',normal_MSC_screen=True,password_not_collected=True,no_additional_recording_or_mode_request=True,screen_observation_is_not_recording_health_or_rescue_acceptance=True))
put('observer-exec-completion.json',dict(exec_session=57735,exec_exit_code=0,original_live_status='HOST_RETURN_OBSERVED',original_private_peer_accepted=True,raw_frame_saved_before_decode=True,helper_and_observer_absent=True,no_signal_reset_or_retry=True))

gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();g=json.loads(gb);initial=json.loads((D/'goal-status-before-approval.json').read_text())
assert g['authorization_consumption']['Mac_owner_status12']['consumed'] is True
for k in ['requirements','objective','research_priority','prepared_first_device_trial','prepared_root_host_trial']:assert g[k]==initial[k],k
assert not g['persistent_write_release'] and not g['goal_complete']
g['updated_utc']=now;g['latest_stage']=D.name
g['research_activity']='Executed exactly one approved fixed status12 diagnostic. Actual root UID/PID/birth/path plus live self-image HELLO checked. Original kernel-bound private1024B record archived before decoding and accepted; status HOST_RETURN_OBSERVED, native0, cleanup0, pending0, vendor0. Original helper and observer independently absent; exec57735 exit0. One independent cached query matched private before/after HMAC, MSC0 and storage drivers; user confirms normal USB/MSC screen. This completes only Mac ownership/return substep. Do not repeat same status trial. Sony authentication/service entry, camera-local RAM execution, full same-body backup, independent recovery and MAIN HEVC remain unproven. Old11 UNKNOWN retained, all16 unchanged, no firmware write or firstflash release.'
g['prepared_owner_status12_trial'].update(explicitly_authorized=True,staged=True,executed=True,ready_for_new_specific_approval=False,grant_consumed=True,formal_outcome='HOST_RETURN_OBSERVED',host_owner_return_acceptance=True,full_milestone2_complete=False,execution_record=str((D/'README.md').relative_to(R)))
g['authorization_consumption']['Mac_owner_status12'].update(status='EXECUTED_ONCE_HOST_RETURN_OBSERVED',helper_execution_not_yet_verified=False,verified_helper_invocations=1,helper_original_pid=85479,helper_original_process_absent=True,observer_original_process_absent=True,automatic_retry=False,screen_user_report='正常显示USB／MSC，无报错',completed_utc=now)
g['owner_status12_live_execution'].update(status='HOST_RETURN_OBSERVED',original_helper_absent=True,original_observer_absent=True,observer_exec_exit_code=0,helper_kernel_identity_and_live_image_verified=True,accepted_private_completion=True,raw_private_final_archived=True,cached_MSC_and_storage_driver_observed=True,user_screen_normal=True,physical_camera_acceptance=False,scope_completed='Mac USB ownership and trusted return only',Sony_auth_or_camera_RAM_execution_proven=False,execution_record=str((D/'README.md').relative_to(R)))
g['current_native_owner_channel_candidate'].update(explicitly_approved=True,new_integrated_native_executed=True,new_root_or_camera_operations=1,native_or_root_cross_UID_validated=True,root0500_policy_model_only=False,ready_for_specific_status_diagnostic_approval=False,grant_consumed=True,accepted_private_completion=True,bootstrap_supervisor_and_global_fence_ready=True,authenticated_final_result_delivery_ready=True,diagnostic_outcome='HOST_RETURN_OBSERVED',scope_of_completed_evidence='status12 host owner/return only; no Sony authentication or camera program',execution_record=str((D/'README.md').relative_to(R)),native_authentication_scope_released=False)
g['current_Mac_cache_observation'].update(receipt=str((D/'post-trial-cache.json').relative_to(R)),serial_values_selected_used_or_saved=True,raw_serial_saved=False,serial_use='approved in-memory HMAC consistency only',MSC_interface0_observed=True,storage_driver_classes=cache['selected'][0]['storage_driver_classes'],cached_tag_matches_accepted_private_snapshots=True,same_unit_firmware_or_active_USB_health_proven=False)
g['recovery_corrected_owner_status12_package'].update(root_helper_executed=True,new_diagnostic_approved=True,execution_record=str((D/'README.md').relative_to(R)),formal_outcome='HOST_RETURN_OBSERVED',one_shot_consumed=True,milestone2_complete=False)
g['recovery_owner_status12_actual']=dict(readme=str((D/'README.md').relative_to(R)),raw_private_receipt=str((D/'private-record.bin').relative_to(R)),raw_private_sha256=private['record_sha256'],root_helper_invocations=1,host_scope_passed=True,helper_and_observer_exited=True,independent_cached_MSC_match=True,user_screen_normal=True,not_Sony_authentication_camera_RAM_execution_or_recovery=True)
g['next_safe_offline_actions']=[
 '251获准12号诊断实测HOST_RETURN_OBSERVED：root身份/live HELLO、私有原帧接收与解析、原helper及观察器退出、独立缓存同机MSC和用户屏幕正常均完成。关闭Mac接管归还这一子步骤，不再重复同类试验。',
 '下一步只准备Sony通信与相机内RAM空任务入口：复用现有静态证据，明确初始MSC认证、服务切换及退出的实际影响，包括.hasp/模式与持久状态可能写入。请求/绑定/失败退出范围可复核前，不发送Sony命令或上传程序。',
 '新设备范围须以具体固定方案提交；12号、11号、195和05均不可复用。第2里程碑仍缺Sony认证和机内执行，第3完整同机备份、第4独立恢复、第5目标MAIN HEVC、第6最小持久化准入仍未完成；首刷不放行，原11号UNKNOWN不倒填。'
]
assert g['requirements']==initial['requirements']
for k,value in initial['authorization'].items():assert g['authorization'][k]==value
ga=enc(g)
readme='''# FX3 12号单次USB接管与归还诊断结果

**限定主机诊断通过：HOST_RETURN_OBSERVED。** 已执行且仅执行一次root helper，私有完成回执通过，原helper和观察器均退出，独立缓存确认同机MSC及存储驱动，用户确认机身正常显示USB／MSC、无报错。没有Sony认证、读卡、相机程序上传或固件写入。

## 真实证据

- 批准包SHA256：57dc8a85d05360e5df098a75ace9fa422dd31293396c65bb238d2eec5a6a5910。helper PID85479、UID0、启动时间1793426146.455940和固定root路径在运行时由内核核对；同一连接live HELLO的自读程序摘要匹配93d05504640623f56074bf120052c82fdfd3f21629cc83207e5e0b97380d65dc。
- [原始私有回执](private-record.bin)1024字节，在原已核验连接接收、保存后解码，SHA256为de47d6c9c73aa97c5150a01d6a7acf2ddfbd1b3028116f96f06c7850628b1b55。[原监督器最终记录](live-final-summary.json)为HOST_RETURN_OBSERVED。存档再解码仅作格式/摘要复核，不重建或取代原连接身份。
- 私有结果包含23条事件。接管、接口打开、端点81/02与512字节管道映射、接口释放、设备归还及关闭均返回0；cleanup_error、pending与vendor_attempted均为0。归还后第一次缓存尚未匹配，下一次成功，原始返回码保留于[结构化实测记录](actual-observation.json)。
- 原helper及原观察器通过内核进程查询确认不存在，exec会话57735正常退出0。没有强杀、重置、自动重试或第二次helper调用。
- 一次独立后置缓存查询得到与私有before/after一致的HMAC标签、MSC接口0及MassStorage/SCSI/BlockStorage关联。原生before/after各有3个存储驱动节点。原序列号、原始缓存不落盘；此标签不能证明固件程序身份。[缓存回执](post-trial-cache.json)。
- 用户明确回复已完成12号原生验证，并观察到正常USB／MSC、无报错。未要求录制、拔线或切模式；屏幕正常不代替拍摄、备份或救砖验收。

## 本轮完成什么

已关闭“Mac受控接管MSC接口并取得可信退出证据”子步骤。第250阶段修正的101至109事件解析和原帧留存，现已通过本次真实运行验证。不重复相同范围的接管试验；11号原试验仍为UNKNOWN，不回填通过。

第2里程碑尚缺Sony认证/服务通信及相机内临时程序实际运行。下一步复用既有静态研究，准备这些入口的最小固定请求、影响范围和退出条件，特别核对.hasp/模式状态等可能持久写入；范围可复核且另获具体批准前不发送命令。

完整同机健康备份、独立恢复、目标MAIN 1080p H.265实录和最小持久化准入仍未通过。首刷前第2至6项共5个前置里程碑仍未完成，本次不放行刷写或跨机型系统。

本次授权fx3-702-owner-status-20261030-12已消耗，不可复用。原私有作业和root一次记录保留；12号观察器正常自行关闭，11号旧观察上下文仍按原方案保留，未对其发信号。
'''
put('readme-before-final.md',(D/'README.md').read_bytes())
rp=R/'README.md';rb=rp.read_bytes();text=rb.decode();overview=next(x for x in text.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3第12号实机接管归还结果](<work/sony-firmware-20261024/stage251-authorized-owner-status12/README.md>)：单次实测HOST_RETURN_OBSERVED；root身份/live HELLO、私有原始回执、helper与观察器退出、独立MSC缓存及用户正常屏幕均完成。仅Mac接管归还子步骤通过，无Sony认证/读卡/刷写，下一步研究机内入口。'
assert D.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();assert '最新研究证据为第250阶段。' in text;text=text.replace('最新研究证据为第250阶段。','最新研究证据为第251阶段。',1)
start=text.index('最新进展：');end=text.index('\n\n',start)
text=text[:start]+'最新进展：12号已获准并实际完成一次接管与归还，HOST_RETURN_OBSERVED。原运行中root身份和live HELLO、原始私有回执、helper及观察器退出通过；独立缓存确认同机MSC/驱动，用户屏幕正常。Mac接管归还子步骤关闭，不再重复。11号UNKNOWN保留。[真实结果与原帧](../../work/sony-firmware-20261024/stage251-authorized-owner-status12/README.md)。第2项仍缺Sony认证/服务通信及机内RAM程序实际执行。'+text[end:]
old='进行中；11号已实际执行，身份/HELLO/退出与缓存正常；私有完成回执解析失败；12号修复固定包已准备，待新单次批准'
new='进行中；12号实机Mac接管归还/可信回执/退出通过，MSC缓存与屏幕正常；Sony认证及机内RAM程序入口未通过'
assert old in text;text=text.replace(old,new,1)
old='第2项下一步提交250的完整12号修复包供具体单次批准。包和重枚举后的缓存节点已固定，不再追加相同模型；批准并确认相机卷全部推出后才执行。不能复用已消耗的11号、195或旧05授权，不自动重试/强杀/重置。11号UNKNOWN保留，不以共享页或合成测试倒填通过。'
new='Mac接管归还子步骤已由251实测关闭，不再重复这一项。第2项下一步准备Sony通信与机内RAM空任务入口，先核对初始MSC认证、服务模式及退出的影响（包括可能持久状态写入），形成具体固定方案前不发送Sony命令或上传。新范围另行提交；12号、11号、195与05均已消耗，不复用。完整备份、独立恢复及目标主录尚未通过。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before-final.json',gb),('goal-status-after-final.json',ga),('root-readme-before-final.md',rb),('root-readme-after-final.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma);(D/'README.md').write_text(readme)
receipt=dict(created_utc=now,status='ACTUAL_STATUS12_HOST_RETURN_OBSERVED_NORMAL_MSC_SCREEN',previous_manifest_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),previous_members_reverified=len(previous['files']),approval_bundle_unchanged=True,root_helper_invocations=1,preflight_cache_queries=1,post_trial_cache_queries=1,root_helper_identity_and_live_image_verified=True,private_raw_saved_and_original_live_peer_accepted=True,private_record_sha256=private['record_sha256'],original_helper_and_observer_absent=True,observer_exit_code=0,independent_cached_same_body_MSC_match=True,user_normal_MSC_screen=True,host_scope_passed=True,milestone2_complete=False,Sony_auth_file_upload_or_firmware_scope_released=False,automatic_retry_reset_kill=False,firmware_write=False,old11_unknown_preserved=True,all16_requirements_unchanged=True,goal_complete=False,persistent_write_release=False,heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
files=[]
for p in sorted(D.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage251-actual-status12-owner-return-v1',member_count=len(files),files=files,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(files),manifest_sha256=sha256((D/'final-receipt.json').read_bytes()).hexdigest(),host_scope_passed=True,milestone2_complete=False,first_flash_released=False)))
