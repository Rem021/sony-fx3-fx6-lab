"""Seal own bridge implementation, preserving all real-device admission gates."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
import ast, json, os, plistlib, stat, subprocess

H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage239-parent-SCM-anchor-receiver';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):
    with (H/n).open('xb') as f:f.write(enc(v))
def volume():
    info=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert info['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

volume();assert not (H/'final-receipt.json').exists()
prev=sha(P/'final-receipt.json')
assert prev=='dc360018c9e89354eed01e38b5d3e024e767a4a84288497a53a987bb94039a47'
pm=load(P/'final-receipt.json');assert len(pm['files'])==134
for x in pm['files']:
    p=R/x['path'];assert p.is_file() and not p.is_symlink()
    assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
t=load(H/'runs-bridge-verified/receipt.json')
assert t['status']=='OWN_RUNTIME_PLAN_ANONYMOUS_CLONE_BRIDGE_SCOPED_PASS'
assert t['tests']==8 and len(t['cases'])==27 and t['errors']==t['failures']==0
for name,pin in t['source_hashes'].items():
    assert sha(H/name)==sha(H/'runs-bridge-verified/source-snapshot'/name)==pin
for x in t['cases']:
    s=x['summary'];assert s['borrowed_FDs_unchanged'] and not s['source_accesses'] and not s['root_remaining_anonymous']
cases={x['name']:x['summary'] for x in t['cases']};assert len(cases)==27
for name in ['normal-321','normal-9011','normal-400','normal-90','mutate-caller-plan']:
    s=cases[name];assert s['result']==11 and s['collector_status']==10752 and s['worker_status']==0
    assert s['collector_reaped'] and s['final_mask']==s['original_mask'] and not s['root_remaining_new_FDs']
    assert [x['flags'] for x in s['clones']]==[17,0]
    assert s['clones'][0]['old_file_image_removed_before_first_child_instruction']
    assert [x['type'] for x in s['messages']]==[3,4,1,2]
    assert all(x['plan_sha']==s['original_plan_sha'] and x['image_sha']==t['binary_sha256'] for x in s['messages'])
for name in ['early-other-thread-reap','no-parent-reap','baseline-SIGCHLD-blocked','mask-restore-error']:
    assert cases[name]['result']==2
assert cases['mask-restore-error']['final_mask']!=cases['mask-restore-error']['original_mask']
assert cases['same-capsule-replay']['result']==4
assert t['only_own_ARM64_executed'] and t['all_Linux_VFS_IPC_signal_clock_and_reaper_operations_are_explicit_fakes']
assert not t['actual_Linux_processes_or_threads_created'] and not t['original_Sony_Linux_glibc_or_driver_executed']
assert t['new_device_operations']==0 and not t['probe_deployable'] and not t['first_flash_released']
assert not t['global_cross_reload_owner_or_exclusive_endpoint_origin_proven']
assert not t['Sony_loader_constructor_and_current_target_verified'] and not t['full_boot_worker_integrated']
a=load(H/'relocation-audit.json');repro=load(H/'reproducible-build-summary.json')
assert a['status']=='PASS_FOR_THIS_FIXED_OWN_CAPSULE' and a['relocation_count']==128 and a['arithmetic_checks']==640
assert repro['status']=='PASS' and repro['bytes']==262144 and not repro['deployable']
assert a['binary_sha256']==repro['binary_sha256']==t['binary_sha256']=='0bf01a5c42ea6a7591d30954fea8448d65c45dae28ec2c20b6769e12f188b1b4'
assert sha(H/'build-first/bridge.elf')==sha(H/'reproducible-build/bridge.elf')==t['binary_sha256']
assert repro['tested_source_hashes']==a['tested_source_hashes']==t['source_hashes']
for folder in ['build-first','reproducible-build']:
    build=load(H/folder/'build.json');assert build['sha256']==t['binary_sha256']
    for name,pin in build['source_pins'].items():assert sha(H/name)==sha(H/folder/name)==pin
    for name in ['parent','collector','bridge']:assert (H/folder/(name+'.o.stderr.txt')).read_bytes()==b''
for origin_name in ['builder-origin.json','sha-origin.json']:
    x=load(H/origin_name);assert sha(R/x['path'])==x['sha256']
origin=load(H/'sha-origin.json');text=(R/origin['path']).read_text()
assert text[text.index(origin['start_marker']):text.index(origin['end_marker'])]==(H/'sha_impl.inc').read_text()
replay=load(H/'assembly-replay-receipt.json');assert replay['status']=='PASS'
assert replay['generator_sha256']==sha(H/'assemble_source.py')
for name,pin in replay['files'].items():assert sha(H/name)==sha(H/'assembly-replay'/name)==pin
assert load(H/'source-revisions.json')['clock_unit_conversion_seed_bug_corrected_before_first_build']
first=load(H/'runs-bridge/receipt.json')
for name,pin in first['source_hashes'].items():assert sha(H/'runs-bridge/source-snapshot'/name)==pin
public=load(H/'public-reference-recheck.json')
assert not public['downloaded_content_executed'] and public['device_operations']==0
for x in public['sources']:
    if x['status']=='CAPTURED':assert sha(H/x['path'])==x['sha256'] and (H/x['path']).stat().st_size==x['bytes']
old=load(B/'stage235-single-load-preparation-and-exit-observer/remaining-parent-identity-counterexample.json')
assert old['must_not_release_this_candidate'] and old['current_false_complete']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json')
assert len(release['files'])==23
assert sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json'
assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
prior=json.loads(before);native=load(H/'native-goal-observed.json')
assert native['goal']['status']=='active' and len(prior['requirements'])==16
assert not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R))
scope=dict(status='OWN_RUNTIME_PLAN_AND_ANONYMOUS_CLONE_BRIDGE_CONDITIONAL_PASS_NOT_DEVICE_ADMITTED',
    own_checks=8,own_model_cases=27,relocation_references=128,relocation_arithmetic_checks=640,
    own_ELF_bytes=262144,own_ELF_sha256=t['binary_sha256'],
    own_C_creates_outer_and_inner_channels_and_processes=True,runtime_PID_FD_plan_digest_and_expiry_bound=True,
    child_model_survives_original_file_and_plan_unmap_before_first_instruction=True,
    outer_SIGCHLD_inner_clone0_reaping_contract_modeled=True,
    image_hash_zero_normalizes_BSS_and_is_not_authorization=True,
    mask_restore_fault_leaves_changed_state_and_remains_HELD=True,
    actual_Sony_constructor_and_trusted_preparer_integrated=False,
    global_cross_reload_exclusion_and_endpoint_exclusivity_proven=False,
    prior_two_origin_and_domain_boundary_counterexamples_retained=True,
    actual_kernel_signal_cache_stack_and_resource_completion_proven=False,
    full_boot_worker_integrated=False,probe_deployable=False,
    stage235_candidate_unchanged_and_admission_still_failed=True,
    new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,
    original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,
    all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,
    root195_pending_unlaunched=True,previous_goal_turn_classification='progress:239 C parent receiver ACK and SCM source contract sealed',
    goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,
    previous_members_reverified=134,tests='runs-bridge-verified/receipt.json',
    relocation_audit='relocation-audit.json',source_assembly_replay='assembly-replay-receipt.json',**scope))
new=deepcopy(prior)
new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',
    research_activity='Own C bridge now captures complete runtime plan, validates fixed own image using zero-normalized BSS hash, creates anonymous R/RX/R/RW copy and socketpairs, clones outer SIGCHLD collector inside that copy, receives live proc-object anchor and ACKs before inner clone0 NOOP worker. Model removes old file/plan before first child instruction. Runtime PID/TID/FD/full-plan SHA/expiry replace fixtures; parent restores saved mask only after Z/10752 then waits original-object detach. 8checks27cases, identical262144B builds,128relocations640rebase checks. Mask restore fault remains changed-state HELD. Actual Sony constructor/preparer/global cross-reload ownership/endpoint origin and full boot reader are not integrated; real signals/cache/stack/time/resources/USB and backup/AP recovery/MAIN HEVC unverified. No device/root. All16/formal23/0.4/0.5/195 preserved; first flash not released.')
new['progress_audit']['classification']='progress'
new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('240把239接收器与监管核心接入自写运行时计划/匿名副本/真实C clone路径，外层SIGCHLD/内层clone0；8检查27模型场景与重复构建、128地址引用640重定位算术核对通过。原映射首条子指令前移除仍完成；所有Linux/回收行为仍为模型。掩码恢复失败留下改变状态且HELD；真实构造入口/准备器/全局跨加载排他未接，来源和子域边界保留。全16/195/正式包不变，无设备/root，不能首刷。')
ev=dict(readme=rel+'/README.md',bridge=rel+'/bridge.c',parent=rel+'/parent.c',collector=rel+'/collector.c',
    builder=rel+'/bridge_build.py',model=rel+'/model_bridge.py',tests=rel+'/runs-bridge-verified/receipt.json',
    relocation_audit=rel+'/relocation-audit.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage240_runtime_plan_and_anonymous_clone_bridge']=ev
new['recovery_runtime_plan_anonymous_clone_bridge']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],
    status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=[
    '将240 runtime bridge接到234/235完整计划准备和Sony直接加载构造ABI。现_start只给测试地址，235计划的镜像绑定不适用新capsule；不以新BSS entered代替全局跨加载排他/可信控制端或端点独占。先形成无源读取的可审查入口候选，不投放。',
    '核对真实加载线程/进程及全局所有权，接入有界结果回传，保留239两个来源/子域边界与不可识别SCM权利UNKNOWN。外层SIGCHLD回收时序和掩码恢复故障当前不充真实Linux或Sony服务归还；不靠改成功码、重试/杀进程消除未知。',
    '入口/归还合同闭合后再接完整boot采集与主机回传；同机健康备份、独立AP救砖/逆写逐字节核对和冷启动，以及MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16项仍须全部完成。195root01未批准不启动，正式0.4/0.5及23源码不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:
    assert new[key]==prior[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3运行时计划与匿名副本启动桥](<'+rel+'/README.md>)：自写C创建/接收/监管接通，8检查27模型场景及重复构建、128地址引用640核对通过；外层SIGCHLD与内层clone0，旧映射移除仍运行。真实构造/准备/全局跨加载排他及恢复未闭合；无设备/root，不能首刷。'
assert ib.decode().count(marker)==1 and entry not in ib.decode()
ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode();after=enc(new)
(H/'goal-status-after.json').open('xb').write(after)
(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
for destination,data in [(canonical,after),(index,ia)]:
    tmp=H/('.'+destination.name+'.tmp')
    with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,destination)
members=[]
for p in sorted(H.rglob('*')):
    mode=p.lstat().st_mode
    if stat.S_ISDIR(mode):continue
    assert stat.S_ISREG(mode) and not p.is_symlink()
    members.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage240-own-runtime-plan-anonymous-clone-bridge-seal-v1',
    created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),
    mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),
    goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),
                      first_flash_released=False)))
