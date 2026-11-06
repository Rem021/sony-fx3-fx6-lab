"""Save the bounded decision and update only live progress indexes with guards."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json, plistlib, subprocess, copy

H=Path(__file__).resolve().parent; B=H.parent; R=B.parents[1]
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert v.get('MountPoint')=='/Volumes/KAFU2T'
assert v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/'final-receipt.json').exists(), 'Do not replay a sealed update'
def digest(data): return sha256(data).hexdigest()
def save(name,data):
    with (H/name).open('xb') as f: f.write(data)
def encoded(value): return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()

previous=B/'stage243-result-readback-original-command-contract/final-receipt.json'
assert digest(previous.read_bytes())=='43b0f91d07fab104b9b41dd17eafd8c653571a74b62a020877ef3b3ed233c5e3'
old_seal=json.loads(previous.read_text())
for item in old_seal['files']:
    raw=(R/item['path']).read_bytes()
    assert len(raw)==item['bytes'] and digest(raw)==item['sha256'],item['path']
contract=json.loads((H/'static-contract.json').read_text())
decision=json.loads((H/'decision.json').read_text())
assert contract['source_ranges']==12 and len(contract['instruction_checks'])==71
assert len(contract['core_records'])==3 and not decision['milestone2_complete']

goal_path=B/'GOAL_STATUS.json'; before=goal_path.read_bytes(); goal=json.loads(before)
assert before==(previous.parent/'goal-status-after.json').read_bytes()
protected=('authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority')
protected_before={k:copy.deepcopy(goal[k]) for k in protected}
assert len(goal['requirements'])==16 and not goal['persistent_write_release']
assert goal['goal_manager_status']=='cleared_by_user'
root_path=R/'README.md'; root_before=root_path.read_bytes()
road_path=R/'outputs/fx3-recovery-adapter/ROADMAP.md'; road_before=road_path.read_bytes()
root_text=root_before.decode();road=road_before.decode()
assert H.name not in root_text and '最新研究证据为第243阶段。' in road
overview=next(line for line in root_text.splitlines() if line.startswith('- [FX3实施路线与当前进度]'))
entry='- [2026-10-30 FX3首次程序试验的通信路径判定](<work/sony-firmware-20261024/stage244-highcapacity-session-admission/README.md>)：补齐3条原命令表、同步队列和回调静态连接；共享DMM/路径及挂载边界未满足，现有文件回传候选保持不放行。路线第2项未完成，本批无需连接相机，无设备操作。'
root_after=root_text.replace(overview,overview+'\n\n'+entry,1).encode()
road=road.replace('最新研究证据为第243阶段。','最新研究证据为第244阶段。',1)
needle='目标1080p H.265主录没有实机成片。'
assert needle in road
road=road.replace(needle,needle+'\n\n最新判定：原厂类别与接收端静态连接已核对；现有GET_FILE2回传路线保持不放行。尚未形成可执行真机诊断，本批无需接线。[具体依据](../../work/sony-firmware-20261024/stage244-highcapacity-session-admission/README.md)。',1)
road=road.replace('本次仅整理流程与证据索引，没有新增联网查询、设备访问、管理员操作或固件写入，也没有重建自动目标。','本路线表不授权设备访问、管理员操作或固件写入；自动目标不因路线表更新而重建。',1)
road_after=road.encode()
now=datetime.now(timezone.utc).isoformat()
goal['updated_utc']=now;goal['latest_stage']=H.name
goal['recovery_session_admission_static_decision']={
 'readme':str((H/'README.md').relative_to(R)), 'decision':str((H/'decision.json').relative_to(R)),
 'static_contract':str((H/'static-contract.json').relative_to(R)),
 'roadmap':'outputs/fx3-recovery-adapter/ROADMAP.md',
 'milestone':2,'milestone_complete':False,
 'static_command_records_queue_registration_and_callback_bound':True,
 'current_RAM_GET_FILE2_route_released':False,
 'native_global_DMM_and_selected_path_exclusive_session_verified':False,
 'non_mnt_mount_wrapper_chain_bound_not_proof_of_no_persistent_effects':True,
 'new_device_USB_admin_or_firmware_operations':0,
 'prior_model_tests_repeated':0,
 'result':'bounded route decision delivered; camera connection not needed for this batch'}
goal['next_safe_offline_actions']=[
 '第2里程碑：固定最小通信诊断的代码、命令白名单、身份前置、预算与退出判据；不上传、不选路径、不文件GET、不切模式。先说明认证副作用及主机控制端前置，不启动或重新申请195。',
 '244已交付现有GET_FILE2回传路线的不放行结论。只有取得原厂全局DMM/路径的整段排他及副作用证据，或另一条有界回传机制，才重新审查；没有新输入不重复同一模型案例。',
 '路线第2项未完成，首刷前第2至6项共5个前置未通过；G01至G16、恢复优先、正式0.4/0.5及23源码保持。不得把静态登记、局部结果或正常升级当同机备份/独立救砖/主录验收，自动目标不重建。']
goal['current_native_goal_observation']={
 'receipt':str((H/'native-goal-observed.json').relative_to(R)), 'observed_utc':now,
 'status':'none','source':'native get_goal read only','user_cleared_goal':True,
 'research_continued_by_direct_user_request':True,'goal_recreated':False,'device_authorization_expanded':False}
goal['goal_complete']=False;goal['persistent_write_release']=False
assert {k:goal[k] for k in protected}==protected_before
after=encoded(goal)
save('goal-status-before.json',before);save('goal-status-after.json',after)
save('readme-before.md',root_before);save('readme-after.md',root_after)
save('roadmap-before.md',road_before);save('roadmap-after.md',road_after)
save('native-goal-observed.json',encoded({'goal':None,'observed_utc':now,'recreated':False}))
save('public-source-review.json',encoded({
 'reviewed_utc':now,'source':'https://github.com/YuuLuo/a7c2-service-preload',
 'observed_scope':'Maintainer limits observed execution to ILCE-7CM2 2.01; permanent update admission is separate.',
 'proof_of_FX3_compatibility':False,
 'fixed_chocotan_page':'web fetch cache miss; no change inferred; no code imported or executed'}))

# Every live head must still be the read-derived version before any head update.
assert goal_path.read_bytes()==before and root_path.read_bytes()==root_before and road_path.read_bytes()==road_before
goal_path.write_bytes(after);root_path.write_bytes(root_after);road_path.write_bytes(road_after)
assert goal_path.read_bytes()==after and root_path.read_bytes()==root_after and road_path.read_bytes()==road_after
receipt={
 'created_utc':now,'status':'STATIC_SESSION_CHAIN_BOUND_CURRENT_RESULT_READ_ROUTE_HELD',
 'milestone':2,'milestone_complete':False,'persistent_first_flash_prerequisites_remaining':5,
 'previous_stage_members_reverified':len(old_seal['files']),
 'source_ranges':12,'instruction_checks':71,'command_records':3,
 'previous_model_tests_repeated':0,'new_device_USB_cache_admin_or_firmware_operations':0,
 'original_Sony_glibc_Linux_or_downloaded_camera_code_executed':False,
 'formal_tools_changed':False,'protected16_requirements_and_authorizations_unchanged':True,
 'root195_not_started_or_reapproved':True,'native_goal_observed_none_not_recreated':True,
 'initial_host_audit_failure_retained':True,
 'live_head_sha256':{'goal':digest(after),'root_readme':digest(root_after),'roadmap':digest(road_after)},
 'goal_complete':False,'persistent_write_release':False}
save('verification-receipt.json',encoded(receipt))
files=[]
for path in sorted(H.rglob('*')):
    if path.is_file():
        data=path.read_bytes();files.append(dict(path=str(path.relative_to(R)),bytes=len(data),sha256=digest(data)))
seal=dict(schema='fx3-stage244-bounded-communication-route-decision-v1',
          previous_manifest_sha256=digest(previous.read_bytes()),files=files,member_count=len(files),
          mutable_heads_not_manifest_members=True,**receipt)
save('final-receipt.json',encoded(seal))
print(json.dumps(dict(status=receipt['status'],sealed_members=len(files),
                     seal_sha256=digest((H/'final-receipt.json').read_bytes()),milestone2_complete=False,new_camera_operations=0)))
