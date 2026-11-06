"""Seal the actual one-shot outcome; no new launch, USB API or cache query."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,plistlib,subprocess,sys

D=Path(__file__).resolve().parent;B=D.parent;R=B.parents[1];H=B/'stage248-fixed-owner-status-launch-package'
assert R==Path('/Volumes/KAFU2T/AI/Projects/Mac')
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID')=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (D/'final-receipt.json').exists()
def enc(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,x):
    data=x if isinstance(x,bytes) else enc(x)
    fd=os.open(D/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data)
previous=json.loads((H/'final-receipt.json').read_text())
for x in previous['files']:
    p=R/x['path'];raw=p.read_bytes();assert len(raw)==x['bytes'] and sha256(raw).hexdigest()==x['sha256'],x['path']
assert sha256((H/'approval-bundle.json').read_bytes()).hexdigest()=='c372c53f14b746ad9e9f04ad50c94af5890a7320dccf73ff354179eed0bcff41'
obs=json.loads((D/'actual-observation.json').read_text());cache=json.loads((D/'post-trial-cache.json').read_text());fix=json.loads((D/'host-fix-test-receipt.json').read_text())
assert obs['formal_trial_status']=='UNKNOWN_PRIVATE_RECEIPT_DECODER_ERROR' and fix['status']=='PASS_HOST_ONLY_REGRESSION'
sys.path.insert(0,str(H));import controller_ipc as I
ipc=I.IPC();grant=I.Grant.from_buffer_copy((D/'shared-after-readonly.bin').read_bytes(),ipc.grant_offset)
helper=ipc.probe(obs['helper_identity']['original_pid']);observer=ipc.probe(grant.observer)
assert helper is None
now=datetime.now(timezone.utc).isoformat()
put('final-process-observation.json',dict(observed_utc=now,original_helper_absent=True,original_helper_pid=obs['helper_identity']['original_pid'],original_observer_identity=observer.__dict__ if observer else None,observer_exec_session=8060,observer_preserved_without_signal=True,helper_or_controller_signalled=False))
put('user-physical-observation.json',dict(observed_utc=now,user_report='正常显示USB／MSC，无报错',scope='screen observation only',recording_backup_recovery_or_flash_acceptance=False))
put('user-native-validation-confirmation.json',dict(observed_utc=now,user_report='已完成本次原生验证',no_password_collected=True,validation_not_repeated=True))

gp=B/'GOAL_STATUS.json';gb=gp.read_bytes();g=json.loads(gb);initial=json.loads((D/'goal-status-before-approval.json').read_text())
for k in ['requirements','objective','research_priority','prepared_first_device_trial','prepared_root_host_trial']:
    assert g[k]==initial[k],k
assert g['persistent_write_release'] is False and g['goal_complete'] is False
g['updated_utc']=now;g['latest_stage']=D.name
g['research_activity']='Executed exactly one approved fixed owner-status11 root helper on Mac. Kernel UID/PID/birth/path plus live self-image HELLO verified. Helper original process absent; same-body HMAC/MSC/storage-driver cache observed and user screen normal. Native shared/relay data indicate capture/claim/return with zero cleanup error, but live private receipt rejected: decoder omitted native diagnostic substeps101..109. Raw final private frame was not archived before rejection; formal outcome remains UNKNOWN. Preserved original observer8060, no signal/reset/retry. Derived host-only parser/raw-archive/observer-exit repair, 10 targeted regressions pass; no new native launch. Same-body backup, independent restore and MAIN HEVC remain unproven.'
g['prepared_owner_status11_trial'].update(explicitly_authorized=True,staged=True,executed=True,ready_for_new_specific_approval=False,grant_consumed=True,formal_outcome='UNKNOWN_PRIVATE_RECEIPT_DECODER_ERROR',actual_new_root_or_camera_acceptance=False,execution_record=str((D/'README.md').relative_to(R)))
g['authorization_consumption']['Mac_owner_status11'].update(status='EXECUTED_ONCE_UNKNOWN_PRIVATE_RECEIPT_DECODER_ERROR',helper_execution_not_yet_verified=False,verified_helper_invocations=1,helper_original_pid=79897,helper_original_process_absent=True,automatic_retry=False,screen_user_report='正常显示USB／MSC，无报错',completed_utc=now)
g['owner_status11_live_execution'].update(status='UNKNOWN_PRIVATE_RECEIPT_DECODER_ERROR',original_helper_absent=True,original_observer_retained=True,helper_kernel_identity_and_live_image_verified=True,accepted_private_completion=False,private_final_raw_not_archived=True,cached_MSC_and_storage_driver_observed=True,physical_camera_acceptance=False,user_screen_normal=True,host_only_fix_tests=10,host_only_fix_is_not_a_new_launch_package=True)
g['current_native_owner_channel_candidate'].update(explicitly_approved=True,new_integrated_native_executed=True,new_root_or_camera_operations=1,native_or_root_cross_UID_validated=True,root0500_policy_model_only=False,ready_for_specific_status_diagnostic_approval=False,grant_consumed=True,accepted_private_completion=False,diagnostic_outcome='UNKNOWN_PRIVATE_RECEIPT_DECODER_ERROR',identity_validation_scope='kernel UID/PID/birth/path and live self-image HELLO only; final private receipt not accepted',execution_record=str((D/'README.md').relative_to(R)),host_fix_candidate=str((D/'host-receipt-fix.patch').relative_to(R)))
g['current_Mac_cache_observation'].update(receipt=str((D/'post-trial-cache.json').relative_to(R)),serial_values_selected_used_or_saved=True,raw_serial_saved=False,serial_use='approved in-memory HMAC consistency only',MSC_interface0_observed=True,storage_driver_classes=cache['selected'][0]['storage_driver_classes'],cached_tag_matches_native_shared_snapshots=True,same_unit_firmware_or_active_USB_health_proven=False)
g['recovery_fixed_owner_status_package'].update(new_integrated_root_or_camera_executed=True,ready_for_specific_diagnostic_approval_only=False,execution_record=str((D/'README.md').relative_to(R)),formal_outcome='UNKNOWN_PRIVATE_RECEIPT_DECODER_ERROR')
g['next_safe_offline_actions']=[
 '249已执行一次11号获准诊断，实际root身份和live HELLO通过、原helper已退出、缓存MSC与驱动回归、用户屏幕正常；私有回执因主机解析器漏101..109被拒，UNKNOWN保留，不重复试验。',
 '主机解析器、原始回执先存后解码、确认helper退出后仅关闭观察器的修复候选已完成10项针对性回归。下一步将修复接入完整固定包，重新核对重枚举后的缓存节点与新单次标记；不复用11号、旧05或195授权。',
 '完整新包准备好后再提交一次具体诊断供批准；确认前不启动管理员或USB操作。不以本次共享页/relay、缓存、屏幕或合成测试倒填可信完成、独立救砖或首刷通过。'
]
assert g['requirements']==initial['requirements']
for k,value in initial['authorization'].items():assert g['authorization'][k]==value
ga=enc(g)

readme='''# FX3 11号单次USB接管与归还诊断结果

本次按用户明确批准的第248阶段固定包，仅执行一次管理员helper。**正式结论：UNKNOWN，私有完成回执解析失败；没有自动重试，没有固件写入。** 用户确认相机正常显示USB／MSC，无报错。

## 已取得的实机证据

- 固定缓存目标核对通过。实际helper PID79897、UID0、启动时间和固定路径在运行中由内核核对；同一连接的自读HELLO摘要匹配批准构建65daada1f1cae3e19e6b6ccda848bc62ce736ad1f060b7143ac8e36486e554b4。
- 原helper已通过内核查询确认不存在。单次授权已消耗，旧观察器保留于exec会话8060；没有给helper或观察器发送终止信号、复位或重启。
- 一次独立的后置USB缓存查询看到同一HMAC一致性标签、MSC接口0及MassStorage/SCSI/BlockStorage驱动类别；原序列号和原始缓存不落盘。用户另行观察到相机正常MSC。
- 主机共享页与relay报告的摘要一致。共享页记录接管、接口打开、端点81/02、归还和关闭返回0，清理错误为0，Sony/vendor尝试为0。归还后首次缓存匹配失败，后一次匹配成功。这些资料仍为主机可写的辅助记录，不能替代被拒的私有完成回执。

## 明确失败原因与修复

主机receipt_receiver.py只接受事件阶段1至13；原生owner_iokit.c还记录101至109的接口API子步骤。本次23条事件含102至109，故在“private event phase”检查处被拒。这是自写主机解析器遗漏，未得到相机错误证据。

原监督器又在解码前清空接收缓冲，且未先保存原始1024字节帧。因此本次不能恢复原始私有回执，也不把共享页重新包装后称为真回执。原试验和第248固定包均保留。

[修复补丁](host-receipt-fix.patch)在独立候选中允许明确的101至109、先保存原始帧再解码，并在出错后独立确认helper已消失时，仅结束观察器、保持UNKNOWN；helper仍在或查询失败时保留原实例。10项[针对性回归](host-fix-test-receipt.json)通过，包括复现旧错误、真实23事件的合成封装、越界阶段/摘要拒绝、拒收原帧留存和进程退出反例。这些检查没有root、USB或相机操作。修复候选尚不是新的可执行批准包，也未注入原观察进程。

## 下一步与当前边界

将修复接入完整固定包，绑定重枚举后的新缓存节点，形成新的单次诊断方案后再提交批准；不会自动再次启动。11号、195或旧05授权均不可复用。

本次没有Sony认证、模式/文件命令、读卡、相机程序上传或固件写入。真机入口的可信结果、同机健康备份、独立救砖和目标MAIN 1080p H.265仍未通过。第2里程碑未完成，首刷前第2至6项共5个前置仍未完成。

批准标识：fx3-702-owner-status-20261030-11。批准包SHA256：c372c53f14b746ad9e9f04ad50c94af5890a7320dccf73ff354179eed0bcff41。
'''
readme_before=(D/'README.md').read_bytes();put('readme-pending-snapshot.md',readme_before)

rp=R/'README.md';rb=rp.read_bytes();text=rb.decode()
old='- [2026-10-30 FX3第11号单次诊断执行记录](<work/sony-firmware-20261024/stage249-authorized-owner-status11/README.md>)：已获具体授权并核对固定缓存节点，Terminal启动已提交；等待原生验证与helper身份/结果，不自动重试，尚未确认USB接管或归还成功。'
new='- [2026-10-30 FX3第11号单次诊断执行记录](<work/sony-firmware-20261024/stage249-authorized-owner-status11/README.md>)：已实际执行一次root/USB诊断；内核身份与live HELLO通过、helper退出、缓存MSC/驱动恢复且机身屏幕正常。主机解析器漏101–109子步骤，私有完成回执未保存，正式UNKNOWN；独立修复候选10项回归通过，无重试/刷写。'
assert text.count(old)==1;ra=text.replace(old,new,1).encode()
mp=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=mp.read_bytes();text=mb.decode();assert '最新研究证据为第248阶段。' in text
text=text.replace('最新研究证据为第248阶段。','最新研究证据为第249阶段。',1)
start=text.index('最新进展：');end=text.index('\n\n',start)
text=text[:start]+'最新进展：11号诊断已获准并实际执行一次；root身份和live HELLO核对成功、helper已退出、独立缓存看到同机MSC与存储驱动，用户确认屏幕正常。主机解析器漏掉原生101–109子步骤且未先保存私有原帧，正式结果仍为UNKNOWN。修复候选10项针对性回归通过，没有重复设备试验。[实际记录与修复](../../work/sony-firmware-20261024/stage249-authorized-owner-status11/README.md)。'+text[end:]
text=text.replace('进行中；主机实测和代码整合通过，原生启动/目标绑定/单次包已准备；新接管归还诊断待批准与实机验收','进行中；11号已实际执行，身份/HELLO/退出与缓存正常；私有完成回执解析失败，修复候选待接入新固定包',1)
old='第2项下一步执行248固定的单次接管/归还诊断，须先取得新范围批准并由用户手动推出全部相机卷。未批准时保留包，不再追加同类模型；执行中不自动重试/强杀/重置，无法确认时保留UNKNOWN。195授权已用完，不覆盖本方案。'
new='第2项下一步将249的解析器/原始回执留存修复接入完整固定包，并重新固定重枚举后的缓存节点。新包准备好后再提交具体单次批准；不复用已消耗的11号、195或旧05授权，不自动重试/强杀/重置。本次UNKNOWN保留，不以共享页或合成测试倒填通过。'
assert old in text;text=text.replace(old,new,1);ma=text.encode()
for name,data in [('goal-status-before-final.json',gb),('goal-status-after-final.json',ga),('root-readme-before-final.md',rb),('root-readme-after-final.md',ra),('roadmap-before.md',mb),('roadmap-after.md',ma)]:put(name,data)
assert gp.read_bytes()==gb and rp.read_bytes()==rb and mp.read_bytes()==mb
gp.write_bytes(ga);rp.write_bytes(ra);mp.write_bytes(ma);(D/'README.md').write_text(readme)
receipt=dict(created_utc=now,status='ACTUAL_SINGLE_TRIAL_UNKNOWN_HOST_RECEIPT_DECODER_ERROR',previous_stage_sha256=sha256((H/'final-receipt.json').read_bytes()).hexdigest(),previous_members_reverified=len(previous['files']),approval_bundle_unchanged=True,root_helper_invocations=1,preflight_cache_queries=1,post_trial_cache_queries=1,root_helper_identity_and_live_image_verified=True,original_helper_absent=True,original_observer_preserved=True,accepted_private_completion=False,raw_private_final_not_archived=True,user_screen_normal_MSC=True,host_only_fix_checks=10,automatic_retry_reset_or_kill=False,firmware_write=False,all16_requirements_unchanged=True,goal_complete=False,persistent_write_release=False,heads_sha256=dict(goal=sha256(ga).hexdigest(),root_readme=sha256(ra).hexdigest(),roadmap=sha256(ma).hexdigest()))
put('verification-receipt.json',receipt)
files=[]
for p in sorted(D.rglob('*')):
    if p.is_file():
        raw=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
put('final-receipt.json',dict(schema='fx3-stage249-actual-owner-status11-v1',member_count=len(files),files=files,**receipt))
print(json.dumps(dict(status=receipt['status'],members=len(files),manifest_sha256=sha256((D/'final-receipt.json').read_bytes()).hexdigest(),all16_unchanged=True,trial_retried=False)))
