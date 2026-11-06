"""Archive the completed authorized HOST_ONLY result, without launching anything."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,copy,plistlib,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/'final-receipt.json').exists()
def sha(b):return sha256(b).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def save(name,data):
 if not isinstance(data,bytes):data=enc(data)
 with (H/name).open('xb') as f:f.write(data)
prev=B/'stage245-minimal-communication-admission';pm=(prev/'final-receipt.json').read_bytes()
assert sha(pm)=='becbced1aecec6918cde7379b163770577dc8766465f415d4df7d71a6329a75b'
ps=json.loads(pm)
for item in ps['files']:
 raw=(R/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
fixed=B/'stage195-root-host-validation-plan';bundle=(fixed/'approval-bundle.json').read_bytes()
assert sha(bundle)=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
for item in json.loads(bundle)['files']:
 raw=(fixed/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
actual=json.loads((H/'actual-verification.json').read_text())
assert actual['status']=='HOST_ONLY_ROOT_TRIAL_AND_AUTHENTICATED_READBACK_SCOPED_PASS'
assert actual['host_helper_invocations']==2 and actual['execution_process_exit_code']==0
assert actual['camera_or_USB_operations']==0 and not actual['physical_camera_acceptance']
assert all(not row['original_helper_incarnation_present'] for row in actual['exit_observation'])
gpath=B/'GOAL_STATUS.json';gb=gpath.read_bytes();assert gb==(H/'goal-status-authorized.json').read_bytes()
g=json.loads(gb);protected={k:copy.deepcopy(g[k]) for k in ('authorization','requirements','prepared_first_device_trial','research_priority')}
assert len(g['requirements'])==16 and g['latest_stage']==H.name
now=datetime.now(timezone.utc).isoformat()
g['updated_utc']=now
g['prepared_root_host_trial'].update(root_candidate_executed=True,administrator_or_camera_operations=2,
 admin_helper_invocations=2,camera_operations=0,released_for_execution=False,
 user_job_or_root_artifact_staged=True,status='completed_scoped_host_pass_single_grant_consumed',
 actual_receipt=str((H/'actual-verification.json').relative_to(R)),authorization_consumed=True)
g['current_host_root01_execution'].update(state='HOST_ONLY_SCOPED_PASS_COMPLETE',
 actual_receipt=str((H/'actual-verification.json').relative_to(R)),host_helper_invocations=2,
 original_helpers_exited=True,relay_returncode=0,authorization_consumed=True,automatic_retry=False)
g.setdefault('authorization_consumption',{})['Mac_root_host01']={
 'grant_id':'fx3-host-root-20261029-01','completed_utc':now,'helper_invocations':2,
 'consumed':True,'reusable':False,'receipt':str((H/'actual-verification.json').relative_to(R))}
g['recovery_root_host01_actual']={
 'readme':str((H/'README.md').relative_to(R)),'scope':'HOST_ONLY','milestone':2,
 'host_identity_and_protected_readback_substep_passed':True,'milestone_complete':False,
 'root_UIDs_verified':[0,0],'audit_UID':501,'payload_bytes':64,
 'authenticated_trial_and_fresh_nonce_readback':True,'helper_invocations':2,
 'camera_USB_auth_firmware_or_restore_acceptance':False,'new_model_tests':0}
g['next_safe_offline_actions']=[
 '第2里程碑主机前置已完成本次实际验证：root身份/自读握手/受保护归档/新nonce回读/原进程退出。195单次授权已消耗，不再次执行或自动重试。',
 '下一步仅离线整合已实测的主机身份与回执链到原生MSC拥有者；保留native入口关闭，核对端点角色/请求作用域/在途调用及驱动归还，不以改release标志代替集成。新管理员或USB动作另需具体范围与授权。',
 '244文件回传与245不切状态候选仍不放行，相机暂不需要连接；G01至G16、恢复优先和正式0.4/0.5保持，首刷前2至6仍有5个前置未通过。主机通过不充真机、备份或独立救砖，自动目标不重建。']
g['goal_complete']=False;g['persistent_write_release']=False
assert {k:g[k] for k in protected}==protected
ga=enc(g)
root=R/'README.md';rb=root.read_bytes();text=rb.decode()
overview=next(x for x in text.splitlines() if x.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3 Mac管理员身份与回执实测](<work/sony-firmware-20261024/stage246-authorized-host-root01/README.md>)：按195本次授权实际完成两次root试验/回读，身份、自读握手、受保护归档和原进程退出通过，启动链返回0。第2项主机前置推进，授权已消耗；无USB/相机/固件操作，真机入口及恢复仍待验。'
assert H.name not in text;ra=text.replace(overview,overview+'\n\n'+entry,1).encode()
road=R/'outputs/fx3-recovery-adapter/ROADMAP.md';mb=road.read_bytes();text=mb.decode()
assert '最新研究证据为第245阶段。' in text;text=text.replace('最新研究证据为第245阶段。','最新研究证据为第246阶段。',1)
old='最新判定：4操作最小通信候选已评审；START/STOP可能影响其它USB驱动和事件状态，不能满足不切状态保证，因此尚不可执行，相机无需连接。仅主机跨用户身份/受保护回执仍未实测；同一输入不再追加这条方案的离线模型。[具体判定和前置](../../work/sony-firmware-20261024/stage245-minimal-communication-admission/README.md)。'
new='最新实测：Mac仅主机root身份、自读握手、受保护归档、新nonce回读与原进程退出已通过；两次helper已结束，本次授权已消耗。第2项整体仍未完成，当前不需要连接相机。[实际回执](../../work/sony-firmware-20261024/stage246-authorized-host-root01/README.md)。'
assert old in text;text=text.replace(old,new,1)
text=text.replace('进行中；主机接管做过诊断，自写程序在机身执行及可信回传未通过','进行中；Mac仅主机跨用户身份与受保护回执实测通过；真机通信、自写程序执行及可信回传未通过',1)
old='只推进第2项，聚焦原厂DMM会话准入、全局选路径的所有权及副作用、主机身份和结果回传。需要补齐时才增加相关代码和必要验证；已有通过且未改动的检查不重复运行。'
new='只推进第2项：先离线整合已实测的主机身份/回执与原生MSC拥有者，保持原生入口关闭，核对端点、作用域、在途调用和驱动归还。新管理员或USB动作需要新的具体范围与授权；195单次试验已完成，不再重复。只有针对新改动或实际失败才增加必要验证。'
assert old in text;text=text.replace(old,new,1)
text=text.replace('现有195号主机方案不自动启动或重新申请。','244文件回传和245不切状态候选仍不放行；已用完的195授权不覆盖后续操作。',1)
ma=text.encode()
save('goal-status-after.json',ga);save('readme-before.md',rb);save('readme-after.md',ra)
save('roadmap-before.md',mb);save('roadmap-after.md',ma)
save('observer-session.json',{'exec_session_id':78165,'launcher':'fixed stage195 run_approved_host.py',
 'tool_observed_exit_code':0,'final_status':'HOST_TRIAL_AND_READBACK_COMPLETE','restarted':False})
save('build-binding.json',{'approval_bundle_sha256':sha(bundle),'members_reverified':30,
 'root_helper_sha256':'fb150a18a4efc9d827f293b912aa56c21e14488670817256c12b39c1356c32cb',
 'source_build_or_original_bundle_modified':False,'root_helper_invocations':2,'new_model_tests':0})
assert gpath.read_bytes()==gb and root.read_bytes()==rb and road.read_bytes()==mb
gpath.write_bytes(ga);root.write_bytes(ra);road.write_bytes(ma)
assert gpath.read_bytes()==ga and root.read_bytes()==ra and road.read_bytes()==ma
receipt=dict(status=actual['status'],created_utc=now,previous_manifest_sha256=sha(pm),
 prior_stage_members_reverified=len(ps['files']),fixed_approval_members_reverified=30,
 root_helper_invocations=2,authorization_consumed=True,automatic_retry=False,
 original_helpers_exited=True,relay_returncode=0,
 host_identity_and_protected_readback_substep_passed=True,milestone2_complete=False,
 new_camera_USB_cache_Sony_auth_driver_or_firmware_operations=0,new_model_tests=0,
 requirements16_unchanged=True,camera_authorization_unchanged=True,
 automatic_goal_recreated=False,goal_complete=False,persistent_write_release=False,
 live_head_sha256={'goal':sha(ga),'root_readme':sha(ra),'roadmap':sha(ma)})
save('verification-receipt.json',receipt)
files=[]
for p in sorted(H.rglob('*')):
 if p.is_file():
  data=p.read_bytes();files.append(dict(path=str(p.relative_to(R)),bytes=len(data),sha256=sha(data)))
save('final-receipt.json',dict(schema='fx3-stage246-authorized-host01-actual-result-v1',files=files,
 member_count=len(files),mutable_heads_not_manifest_members=True,**receipt))
print(json.dumps(dict(status=actual['status'],members=len(files),manifest_sha256=sha((H/'final-receipt.json').read_bytes()),root_helper_invocations=2,camera_operations=0)))
