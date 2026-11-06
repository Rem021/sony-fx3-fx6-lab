"""Seal changed public evidence without upgrading any real-device gate."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage240-runtime-plan-and-anonymous-clone-bridge';T=R/'outputs/fx3-recovery-adapter'
def load(p):return json.loads(p.read_text())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):
    with (H/n).open('xb') as f:f.write(enc(v))
def volume():
    assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
prev=sha(P/'final-receipt.json');assert prev=='39ad28e39eaaa5feafa93e162d2f5e8d0a088f4d06da45d6a7b32b23dabf58aa'
pm=load(P/'final-receipt.json');assert len(pm['files'])==87
for x in pm['files']:
    p=R/x['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
a=load(H/'delta-audit.json');assert a['status']=='PINNED_FULL_DIFF_VERIFIED_DOCUMENT_ONLY_NO_NEW_FX3_RECOVERY_IMPLEMENTATION'
assert a['changed_paths']==['docs/QEMU_M2_PROGRESS.md'] and a['added_lines']==764 and a['deleted_lines']==0
assert len(a['headings'])==12
assert sha(H/'qemu-new-commits.diff')==a['delta_sha256']=='f411f466d092a94f2967eef412e5666302a8685c375e2e940d3599d4d7e6d32f'
for x in a['source_records']:
    assert (H/x['path']).stat().st_size==x['bytes'] and sha(H/x['path'])==x['sha256']
assert (H/'new-QEMU_M2_PROGRESS.md').read_bytes().startswith((H/'old-QEMU_M2_PROGRESS.md').read_bytes())
execution=load(H/'audit-execution.json')
assert execution['initial_run_exit_code']==0 and sha(H/execution['result_source'])==execution['result_source_sha256']
assert execution['optimized_run_exit_code']==1 and sha(H/'audit_delta.py')==execution['optimized_source_sha256']
for name,pin in execution['result_files'].items():assert sha(H/name)==pin
assert not a['original_firmware_or_downloaded_code_executed'] and a['new_camera_USB_cache_admin_auth_upload_firmware_operations']==0
assert not a['actual_FX3_entry_backup_restore_and_MAIN_HEVC_gates_changed'] and not a['first_flash_released']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json'
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
prior=json.loads(before);native=load(H/'native-goal-observed.json')
assert len(prior['requirements'])==16 and native['goal']['status']=='active'
assert not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R))
scope=dict(status='CHANGED_PUBLIC_HEAD_DOCUMENT_DELTA_VERIFIED_NO_NEW_FX3_RECOVERY_PATH',
    previous_own_bridge_members_reverified=87,public_old_head=a['old_head'],public_new_head=a['new_head'],
    changed_paths=a['changed_paths'],added_document_lines=764,deleted_lines=0,
    author_emulator_logs_not_independent_device_evidence=True,
    first_entry_preparer_constructor_and_cross_reload_integration_still_missing=True,
    full_boot_capture_backup_independent_AP_restore_and_MAIN_HEVC_proven=False,
    own_bridge240_8checks_27model_cases_remain_conditional=True,
    original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,
    new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,
    formal23_sources_release04_05_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
    root195_pending_unlaunched=True,probe_deployable=False,goal_complete=False,persistent_write_release=False,
    previous_goal_turn_classification='progress:240 own runtime plan/anonymous clone bridge implemented and sealed')
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',
    goal_manager_status_last_observed='active',research_activity='240 own C runtime-plan anonymous-clone bridge sealed/readback87members;8checks27modelcases remain conditional. New public ZVE10 HEAD575c707 differs from400313e only in QEMU_M2_PROGRESS.md:764added0deleted, two pinned originals and gitblob prefixes plus exact append verify. Twelve new emulator sections report initramfs/config/queue/GPU-IRQ progress,19startup packets butzero frames/backup-queue block; documented local patch snippets are not new repository recovery source or FX3 real restore proof. 240 initialYuuLuo capture equals pinned228; initial audit completed before interrupt attempt, optimized rerun refused overwrite. First-entry constructor/preparer/global crossload/result gaps explicit. No device/root; all16/formal23/0.4/0.5/195unchanged; firstflash unreleased.')
new['progress_audit']['classification']='progress'
new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('241针对实际变化的公开HEAD固定完整差分及两端原文/Git对象，确认只增764行QEMU文档；12新节含本地中断片段及19启动包但仍零帧/backup阻塞，不充FX3恢复新实现。240的87成员/当前状态核回，明确构造/准备/跨加载/回传接入缺口。初始审查已PASS，后续优化因排他创建拒绝覆盖而停，执行来源分开记录。无设备/root，16/195/正式包不变，不能首刷。')
ev=dict(readme=rel+'/README.md',delta=rel+'/qemu-new-commits.diff',audit=rel+'/delta-audit.json',
    execution=rel+'/audit-execution.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage241_public_recovery_delta_and_first_entry_gaps']=ev
new['recovery_public_delta_and_first_entry_gaps']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],
    status='active',source='native get_goal read only',device_authorization_expanded=False)
# The practical next actions from240 remain in force, rather than substituting another web recheck.
assert new['next_safe_offline_actions']==prior['next_safe_offline_actions']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:
    assert new[key]==prior[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3新公开提交与首次入口接入复核](<'+rel+'/README.md>)：固定ZV-E10新HEAD575c707完整差分，仅文档新增764行；有仿真中断进展但末节仍零帧，无FX3救砖新实现。240的87成员核回；构造/准备/跨加载与回传待接，无设备/root，不能首刷。'
assert ib.decode().count(marker)==1 and entry not in ib.decode()
ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode();after=enc(new)
(H/'goal-status-after.json').open('xb').write(after)
(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
for destination,data in [(canonical,after),(index,ia)]:
    temp=H/('.'+destination.name+'.tmp')
    with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temp,destination)
members=[]
for p in sorted(H.rglob('*')):
    mode=p.lstat().st_mode
    if stat.S_ISDIR(mode):continue
    assert stat.S_ISREG(mode) and not p.is_symlink()
    members.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage241-public-delta-and-first-entry-gaps-seal-v1',created_utc=now,
    previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
