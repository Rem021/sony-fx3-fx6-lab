"""Seal scoped result-pipeline work and observe the user's cleared goal."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage242-DT-INIT-preparation-and-cross-load-claim';T=R/'outputs/fx3-recovery-adapter'
def load(p):return json.loads(p.read_text())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):
 with (H/n).open('xb') as f:f.write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
prev=sha(P/'final-receipt.json');assert prev=='218784e0e0e2768a742f864a0ac4784f848768792713e759dd35ff20b185f3bd'
pm=load(P/'final-receipt.json');assert len(pm['files'])==152
for x in pm['files']:
 p=R/x['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
a=load(H/'candidate-audit.json');t=load(H/'runs-result/receipt.json');native=load(H/'native-result-contract.json')
assert a['status']=='OWN_LOCAL_RECORD_PINNED_DECODER_AND_STATIC_READ_CONTRACT_PASS_NOT_DEVICE_ADMISSION'
assert t['tests']==a['own_checks']==8 and len(t['cases'])==a['receipt_rows']==19 and t['errors']==t['failures']==0
assert a['own_ARM64_model_runs']==16 and a['host_rejection_variants']==28 and a['link_relocations']==231 and a['rebase_arithmetic_checks']==1155
assert native['complete_functions']==a['native_full_functions']==12 and native['instruction_checks']==a['native_instruction_checks']==56
assert sum(len(x['rows']) for x in native['jump_tables'])==a['dispatch_entries']==21
assert t['only_own_ARM64_and_own_host_python_executed'] and t['native_Sony_GET_Senser_glibc_Linux_or_USB_not_executed']
assert t['native_reply_body_in_tests_is_model_serialization'] and t['observed_local_record_never_authorizes_flash_or_global_completion']
assert t['new_device_operations']==0 and not t['current_camera_identity_authenticated_channel_and_exclusive_selected_path_verified']
for n,pin in t['source_hashes'].items():assert sha(H/n)==sha(H/'runs-result/source-snapshot'/n)==pin
assert a['test_source_hashes']==t['source_hashes']
for folder in ['build-initial','reproducible-build']:
 b=load(H/folder/'build.json');p=H/folder/'entry.so'
 assert p.stat().st_size==262144 and sha(p)==b['sha256']==t['binary_sha256']==a['full_file_sha256']=='e009b374283a8f8d0f1c1101f95c5b5d2ec0bd46530440d57f9c94b32ae30232'
 for n,pin in b['source_pins'].items():assert sha(H/n)==sha(H/folder/n)==pin
 for n in ['front','bridge','parent','collector']:assert not (H/folder/(n+'.o.stderr.txt')).read_bytes()
 assert b['immutable_image_id']==a['immutable_image_id']!=a['full_file_sha256'] and not b['deployable']
assert native['original_source_sha256']==sha(R/native['original_source'])=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
assert not native['original_Sony_or_downloaded_code_executed'] and not native['first_flash_released']
assert native['path_selection_and_read_are_separate_and_GET_frees_shared_cell'] and native['operation0_calls_mount_helper_before_file_access']
assert native['getter_fsync_close_and_setter_dlclose_returns_not_checked_by_native_business_status']
for origin in load(H/'candidate-source-origins.json'):assert sha(R/origin['path'])==origin['sha256']
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json'
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
prior=json.loads(before);observation=load(H/'native-goal-observed.json')
assert observation['goal'] is None and observation['user_cleared_goal_then_requested_continue'] and not observation['goal_recreated']
assert len(prior['requirements'])==16 and not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R))
scope=dict(status=a['status'],own_checks=8,own_ARM64_model_runs=16,receipt_rows=19,host_rejection_variants=28,
 full_file_sha256=a['full_file_sha256'],immutable_image_id=a['immutable_image_id'],ELF_bytes=262144,
 native_functions=12,native_instruction_checks=56,native_dispatch_entries=21,rebase_arithmetic_checks=1155,
 own_C_fixed_RAM_local_record_and_externally_pinned_host_decoder_implemented=True,
 valid_core11_record_with_late_report_close_or_clock_failure_retained=True,
 native_get_mount_shared_selected_path_unbounded_allocation_and_unchecked_returns_preserved=True,
 actual_camera_authentication_DMM_session_path_exclusivity_namespace_and_reply_verified=False,
 local_record_is_not_report_close_setter_return_USB_or_full_job_certificate=True,
 original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,
 new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,probe_deployable=False,
 full_boot_backup_independent_AP_restore_MAIN_HEVC_or_first_flash_verified=False,
 formal23_sources_release04_05_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
 root195_pending_unlaunched=True,user_cleared_native_goal_no_automatic_recreation=True,
 work_continued_by_explicit_user_continue=True,previous_turn_classification='progress:242 DT_INIT/preparation/plan2IPC4 and shared-namespace claim implementation sealed',
 goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=152,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='cleared_by_user',goal_manager_status_last_observed='none',
 research_activity='Own C emits fixed256B RAM local-core record; offline host decoder pins external fullfileSHA/nonce/profile/controller, checks imageID/whole-plan2 SHA/targettime and exact260B nativebody, always local-observation-only/no release.8checks16ownARM64runs28host rejection variants;19receipt rows, identical262144B builds and231refs1155rebase arithmetic.12complete original Jiritsu functions56instruction checks21jump entries fix select15/write16/read17 branch mapping and GET0/FF/0 route: mount helper before read, shared path cell freed byGET, whole-file DMM allocation, uncheckedfsync/close/dlclose status. Validcore11record may remain after late publication failure; paired countercases preserved. Actual native GET/auth/DMM/namespace/exclusivepath/wirereply unverified. No device/root/fullboot/restore/MAINHEVC proof. User cleared nativegoal then requestedcontinue;get_goal none, not recreated. All16/formal23/0.4/0.5/195unchanged; firstflash unreleased.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_turn_classification']
new['progress_audit']['basis'].append('243实现自写C固定RAM局部记录与外部文件SHA/关联字段约束的主机解码；8检查16ARM64实例28拒绝变体、重复构建及231引用1155算术通过。12原厂完整函数/56指令/21分派核对GET2有挂载、共享选路径、整文件分配与忽略返回值；记录可在最终发布失败时仍显示核心11，明确只局部观察、禁止自动放行。真实认证/路由/独占/USB与备份恢复主录未证。用户清除自动目标后请求继续，原生goal为空未重建；全部16/195/正式包保留，无设备/root。')
ev=dict(readme=rel+'/README.md',producer=rel+'/front.c',decoder=rel+'/result_protocol.py',tests=rel+'/runs-result/receipt.json',
 native_contract=rel+'/native-result-contract.json',audit=rel+'/candidate-audit.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage243_local_result_and_native_readback_contract']=ev
new['recovery_local_result_and_native_readback_contract']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=observation['observed_utc'],status='none',
 source='native get_goal read only',user_cleared_goal=True,research_continued_by_direct_user_request=True,goal_recreated=False,device_authorization_expanded=False)
new['next_safe_offline_actions']=[
 '以243自有RAM记录为唯一对象，继续核对原厂高容量DMM会话/类别登记及选路径全局所有权。两条内层候选帧不是USB工具，路径逃逸/挂载/实际读取没有安全验证，不发送、不认证、不启动195。',
 '主机已能按外部预期文件SHA与完整计划校验局部记录，仍需真实同机身份/认证通道/控制端准入与Sony同步返回、USB归还证据。保留局部记录可先于最终关闭失败的边界；不自动释放占位、重试或把状态0/11当全任务成功。',
 '完成实际入口和归还前置后整合完整boot采集、主机回传、同机健康备份和独立AP救砖/逆写逐字节核对冷启动；MAIN1080p29.97 HEVC42010约16Mbps/exact30/实际成片音画长录等16项保持。正式0.4/0.5及23源码、195未批准未启动保留，自动目标已清除不自动重建。']
for k in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert new[k]==prior[k]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3局部结果记录与主机回传合同](<'+rel+'/README.md>)：自写C固定RAM记录和外部摘要绑定解码，8检查/16ARM64实例/28拒绝变体及重复构建通过；12原函数56指令21分派固定GET2挂载/全局路径/忽略返回边界。只局部观察，真实回传/恢复未验；无设备/root，不能首刷。'
assert ib.decode().count(marker)==1 and entry not in ib.decode()
ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode();after=enc(new)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
for dest,data in [(canonical,after),(index,ia)]:
 temp=H/('.'+dest.name+'.tmp')
 with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(temp,dest)
members=[]
for p in sorted(H.rglob('*')):
 mode=p.lstat().st_mode
 if stat.S_ISDIR(mode):continue
 assert stat.S_ISREG(mode) and not p.is_symlink()
 members.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage243-local-result-native-read-contract-manual-continuation-seal-v1',created_utc=now,
 previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
 goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),native_goal='none',first_flash_released=False)))
