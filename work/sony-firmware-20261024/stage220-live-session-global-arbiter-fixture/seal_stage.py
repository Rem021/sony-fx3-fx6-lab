"""Register the fixture live-session arbiter. No device or privilege backend."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,shlex,stat,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage219-bound-handoff-and-request-claims';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='5d5e565cf12b5970095315540a71c53892f21e9b0233e5bd06b65438494f8d93'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
MODULE='be0805584b07e116d26da2ee8036a67cbd9c65801efdaedab47e995f33e3030d'
SYNTHETIC='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def encode(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,value):(H/name).open('xb').write(encode(value))
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
assert sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==1873
for row in prior['files']:
    p=R/row['path'];s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256']
main=json.loads((H/'runs-final/receipt/results.json').read_text())
extra=json.loads((H/'runs-boundaries/receipt/results.json').read_text())
assert main['status']=='PASS_LIVE_MEDIATED_FIXTURE_ONLY' and main['tests_run']==10
assert extra['status']=='PASS' and extra['tests_run']==2
for report in (main,extra):
    assert report['errors']==report['failures']==0 and report['new_camera_operations']==0
    assert not report['target_ARM64_entry_global_fence_integrated']
    for name,digest in report['source_hashes'].items():assert sha(H/name)==digest
    assert all(o['all_children_terminal'] for o in report['owners'])
assert len(main['owners'])==12 and sum(o['children'] for o in main['owners'])==20
assert len(extra['owners'])==2 and sum(o['children'] for o in extra['owners'])==3
assert main['module_sha256']==sha(P/'runs-final-v2/built/boot-module.so')==MODULE
assert main['own_ARM64_code_executed'] and not main['Sony_or_Linux_code_executed']
assert not main['real_target_root_UID_or_private_IPC_authority_proven'] and not main['independent_recovery_proven'] and not main['flashable']
full=next(o for o in main['owners'] if Path(o['directory']).name=='full-owner')
assert full['state']=='IDLE' and len(full['history'])==8
assert [j['done']['source_reads'] for j in full['history']]==[128,128,128,126]*2
assert all(j['exit']==0 and j['done']['result']==0 and j['state']=='IDLE' for j in full['history'])
for role in (0,1):
    folder=H/'runs-final'/('assembled-b'+str(role));value=json.loads((folder/'complete.json').read_text())
    assert value['bytes']==33423360 and len(value['windows'])==4 and value['target']=='boot'+str(role)
    assert value['sha256']==sha(folder/('source.boot'+str(role)))==SYNTHETIC
    assert not value['hardware_validated'] and not value['same_body_origin_verified'] and not value['atomic_snapshot_proven']
live=next(o for o in main['owners'] if Path(o['directory']).name=='live-owner')
assert live['children']==1 and live['state']=='HELD_UNKNOWN' and live['history'][0]['done']['result']==23
assert not (H/'runs-final/live-second').exists()
event=main['events'][0];assert event['live'] and not event['second_worker_started']
race=main['events'][1];assert race['all_terminal'] and race['restart_denied'] and sorted(c['claimed'] for c in race['children'])==[False,True]
assert len({c['pid'] for c in race['children']})==2
for name in ('crash-before-done','exit-without-done','post-done-exit-nonzero','bad-nonce','bad-module','extra-frame','deadline','tamper'):
    owner=next(o for o in main['owners'] if Path(o['directory']).name==name+'-owner')
    assert owner['state']=='HELD_UNKNOWN' and len(owner['history'])==1
    if name=='exit-without-done':assert owner['history'][0]['exit']==0 and owner['history'][0]['done'] is None
    if name=='post-done-exit-nonzero':assert owner['history'][0]['exit']==22 and owner['history'][0]['done']['result']==0
assert (H/'runs-final/partial-owner/global-source-session.v1.held').stat().st_size==7
assert all(o['state']=='HELD_UNKNOWN' for o in extra['owners'])
assert extra['owners'][0]['history'][-1]['done']['result']==51 and extra['owners'][0]['history'][-1]['done']['source_reads']==0
assert any('CRC' in reason for reason in extra['owners'][1]['history'][0]['reasons'])
# Inspect current process table, rather than assuming saved all-terminal fields.
owned_pids={j['pid'] for report in (main,extra) for o in report['owners'] for j in o['history']}
owned_pids.update(c['pid'] for c in race['children']);assert len(owned_pids)==25
current=[]
for line in subprocess.check_output(['/bin/ps','-axo','pid=,args='],text=True).splitlines():
    fields=line.strip().split(None,1)
    if len(fields)!=2:continue
    pid=int(fields[0]);args=shlex.split(fields[1]) if 'stage220-live-session-global-arbiter-fixture' in fields[1] else []
    if pid in owned_pids and any(arg in (str(H/'model_worker.py'),str(H/'owner_claim_child.py')) for arg in args):current.append(pid)
assert not current,'same fixture handle/process still live'
failed=json.loads((H/'runs-first/receipt/results.json').read_text())
assert failed['status']=='FAIL' and failed['tests_run']==10 and failed['failures']==1 and failed['errors']==0
for name,digest in failed['source_hashes'].items():assert sha(H/('first-tested-'+name))==digest
design=json.loads((H/'protocol-design.json').read_text());assert sha(R/design['reference']['path'])==design['reference']['sha256']
assert not design['target_entry_currently_forces_this_owner']
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text())
assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link not in ('verification-receipt.json','final-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert old['latest_stage']==P.name and len(old['requirements'])==16 and native['goal']['status']=='active'
assert not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
verification=dict(schema='fx3-stage220-live-arbiter-fixture-verification-v1',created_utc=now,
    status='PASS_12_MEDIATED_FIXTURE_TESTS_TARGET_GLOBAL_ENTRY_STILL_OPEN',
    previous_manifest_sha256=PREV,previous_members_reverified=1873,
    final_main_tests=10,additional_boundary_tests=2,own_ARM64_child_processes=23,owner_race_processes=2,
    final_fixture_processes_currently_live=current,real_Mac_private_channel_and_exit_observation_used=True,
    original_live_blocked_source_denies_second_process=True,normal_same_live_owner_full_boot_regions=['boot0','boot1'],
    synthetic_bytes_per_boot=33423360,synthetic_hash_for_both_roles=SYNTHETIC,real_camera_backup=False,
    private_done_alone_or_exit0_alone_releases_owner=False,late_exit_or_public_completion_releases_UNKNOWN=False,
    repeat_window_result=51,repeat_window_source_reads=0,changed_chunk_CRC_rejected=True,
    failed_observation_and_first_sources_preserved=True,stage219_module_unchanged=MODULE,
    mediated_path_serialization_verified=True,target_ARM64_entry_global_guard_integrated=False,
    direct_target_module_global_gap_remains_open=True,root_cross_UID_IPC_or_protected_path_validated=False,
    trusted_target_launcher_or_completion_verified=False,own_ARM64_code_executed=True,Sony_or_Linux_kernel_or_glibc_executed=False,
    formal_release04_and05_and23_sources_unchanged=True,root01_bundle_and_absent_job_unchanged=True,
    all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,
    goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Implemented fixture-only live session arbiter serializing own ARM64 children via inherited private socket, original Popen normal exit/EOF, bound result, independent byte decoding, unchanged fence and deadline. No persisted record/PID disappearance can resume; UNKNOWN sticky, owner restart denied.10main+2boundary tests,23ownARM64children+2real owner-race processes; boot0+boot1 each4windows/33423360synthetic bytes. Initial fence-drift observation failure fixed without clearing UNKNOWN. Stage219target module unchanged, direct global entry gap remains OPEN; no camera/backend/root/Sony execution.16requirements,195pending,0.4/0.5 unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active persistent goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('220存活会话离线监管入口经实际Mac私有socket和Popen句柄串行启动自写ARM64；阻塞/超时/退出0无DONE/DONE后非0/错误nonce或SHA/重复帧/公开记录改写均保留UNKNOWN，原所有者退出后不自动接替。正常同一会话boot0/boot1各4窗口，33,423,360B/区人工源完整组装；10主+2边界通过、23模型子进程+2所有者竞争，重复窗口51零读与坏块CRC拒绝。修复初轮观察提前返回，无清UNKNOWN。219目标模块未改、直接入口并发缺口仍OPEN，真实IPC/root/备份恢复未验；16要求/195/0.4/0.5保留，无设备/root。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',owner=REL+'/live_arbiter.py',worker=REL+'/model_worker.py',
    tests=REL+'/runs-final/receipt/results.json',boundary_tests=REL+'/runs-boundaries/receipt/results.json',scope=REL+'/implementation-review.json',
    protocol=REL+'/protocol-design.json',module_sha256_unchanged=MODULE,mediated_fixture_path_serialization=True,
    target_ARM64_entry_global_guard_integrated=False,direct_module_global_gap_still_open=True,new_device_operations=0)
new['latest_stage_evidence']['stage220_live_session_arbiter_fixture']=ev
new['recovery_live_session_arbiter_fixture']={**ev,'tests_passed':12,'own_ARM64_child_processes':23,'owner_race_processes':2,
    'full_boot0_and_boot1_four_windows_each_synthetic':True,'private_completion_plus_normal_exit_and_decoding_required':True,
    'persisted_completion_or_PID_disappearance_can_resume':False,'target_root_or_IPC_authority_attested':False,
    'same_body_backup_restore_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01具体问题待答；不从active/继续推导批准，不启动或重问，不扩大相机权限。',
    '220已验证Mac离线存活监管路径，但219ARM64直接入口仍可绕过监管。下一项将私有在途状态、专用完成通道与失败保持占用移植为自写Linux ARM64候选，并关闭受控读取直接旁路；先假内核构建验证，无上传/设备执行。',
    '不能把普通用户测试目录、Python进程或可改记录当成相机root固定资源域/可信恢复检查点。继续核对目标ABI、受保护路径、真实父im/启动者、模块装载与受控退出；原日期副作用/fork失败退出调用者/无超时wait缺口保留。',
    '保留全部16要求，同机健康boot/p1/完整配置、实际数据视图和访问归还、独立AP入口、逆写/冷启动与MAIN1080p29.97 HEVC/长录。当前两份同SHA人工源组装不充真实boot0/boot1备份或救砖验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=encode(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3存活会话全局监管离线入口](<'+REL+'/README.md>)：10主+2边界检查通过，23自写ARM64子进程及2真实所有者竞争；阻塞/迟到/不完整完成保持UNKNOWN，同会话boot0/boot1各4窗口完整组装人工源。219目标模块直接旁路仍OPEN，机内IPC/root/恢复未验；16要求/195/0.5不变，无设备/root。'
assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent head change'
put('verification-receipt.json',verification)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[]
for p in sorted(H.rglob('*')):
    s=p.lstat()
    if stat.S_ISDIR(s.st_mode):continue
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage220-live-session-arbiter-fixture-v1',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=1873,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
    tests_passed=12,own_ARM64_child_processes=23,owner_race_processes=2,
    mediated_fixture_path_serialization_verified=True,target_ARM64_entry_global_fence_integrated=False,
    direct_target_entry_global_gap_remains_open=True,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=12,
    own_ARM64_child_processes=23,owner_race_processes=2,mediated_fixture_path_serialization_verified=True,
    target_entry_integrated=False,requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
