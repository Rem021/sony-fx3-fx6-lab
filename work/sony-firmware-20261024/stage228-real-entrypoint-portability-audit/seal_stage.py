"""Bind a static reachability audit and public-source refresh, no device backend."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage227-zero-arg-bootstrap-and-keeper-handoff';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='2bc69ab8d1394e510a70e4f0270f50a00026f08a7dda895a4593c0335ab80ba1'
previous=json.loads((P/'final-receipt.json').read_text());assert previous['member_count']==1252
for row in previous['files']:
 p=R/row['path'];assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
audit=json.loads((H/'native-loader-audit.json').read_text());assert len(audit['manual_instruction_checks'])==13 and len(audit['source_slices'])==6 and audit['IMDB']['saved_rows_rebound']==225
for key in ['im','IMDB']:
 row=audit[key];p=R/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert audit['callbacks_registered_as_waitable_threads'] and audit['bootstrap227_requires_main_thread'] and not audit['ordinary_app_infra_path_proves_main_thread_eligibility'] and not audit['original_Sony_or_Linux_executed'] and not audit['new_camera_operations']
raw=json.loads((H/'raw-source-capture.json').read_text());assert raw['heads']['cokeenet/zve10-qemu']=='400313ea073269f7a87eab544b44dfc388f19ed9'
for row in raw['files']:
 assert row['returncode']==0;p=H/'reference'/row['output'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
a7=json.loads((H/'a7c2-source-capture.json').read_text())
for row in a7['files']:
 assert row['returncode']==0;p=H/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
dr=json.loads((H/'diff-capture.json').read_text());assert dr['returncode']==0 and sha(H/'reference'/dr['output'])==dr['sha256']
diff=(H/'reference'/dr['output']).read_text();changed=re.findall(r'^diff --git a/(.*?) b/(.*?)$',diff,re.M);assert changed==[('docs/QEMU_M2_PROGRESS.md','docs/QEMU_M2_PROGRESS.md')]
assert sum(l.startswith('+') and not l.startswith('+++') for l in diff.splitlines())==65 and sum(l.startswith('-') and not l.startswith('---') for l in diff.splitlines())==0
sd=(H/'reference/qemu--docs--incidents--SD_UPDATE_RECOVERY.md').read_text();assert '待实测' in sd and '整个流程能否在' in sd
readme=(H/'reference/a7c2--README.md').read_text();assert 'observed on firmware 2.01' in readme and 'preload execution does not permanently disable signature checks' in readme
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();old=json.loads(before)
native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='STATIC_LOADING_CONTEXT_MISMATCH_AND_PUBLIC_RECOVERY_LIMITS_RECONFIRMED',manual_instruction_checks=13,original_slices=6,saved_IMDB_records_rebound=225,source_repositories_rechecked=3,new_qemu_diff_files=1,new_qemu_documentation_lines=65,public_new_recovery_implementation_found=False,native_RAM_loader_or_dispatch_or_host_return_verified=False,own_constructor_or_thread_guard_relaxed=False,actual_backup_restore_or_independent_AP_recovery_verified=False,existing_tests_rerun=False,new_camera_USB_cache_admin_auth_upload_target_execution_or_firmware_writes=0,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=1252,**scope))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Rebound13 raw branch instructions/6 slices/225 official IMDB rows:ordinary app/infra loader callbacks registered as waitable threads, not proof of227main-thread eligibility or own exports registration/repeated dispatch. Rechecked3 public HEADs;QEMU48e6490..400313e diff only65lines of UI/IRQ research notes, no recovery code. A7CII2.01 temporary preload execution not update acceptance;ZVE10 SD whole recovery remains pending real test. Actual FX3 loading/complete healthy backup/independent AP restore/MAIN recording still missing. No device or root operations;16requirements/formal23sources/195pending preserved.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress:227 own zeroarg chain and retained outer-reaper counterexample'
new['progress_audit']['basis'].append('228以官方im/libIMDB原件新增13指令/6切片/225记录绑定，明确常规线程加载与227主线程guard不匹配，零参不证明可达；三上游HEAD重核，新QEMU提交仅65行UI文档，无新增恢复实现，SD全流程仍待实测。后续先追真实入口与上下文，不继续用模拟包装替代。无设备/root动作，16要求/195/正式包保持。')
ev=dict(readme=rel+'/README.md',audit=rel+'/native-loader-audit.json',verification=rel+'/verification-receipt.json',public_heads=rel+'/raw-source-capture.json',diff=rel+'/reference/qemu-new-commits.diff',scope=scope)
new['latest_stage_evidence']['stage228_real_entrypoint_portability']=ev;new['recovery_real_entrypoint_portability_audit']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['针对当前FX3原厂具体服务/子进程入口，核对路径可控性、持久副作用、父子/线程上下文和完成回传；普通IMDB线程路线不满足227主线程条件，先选真实路线再适配，不能直接放宽guard。','继续定位FX3专用独立AP恢复的触发/硬件初始化与同机健康启动区来源；ZVE10/Pico/SD经验及新UI文档不充FX3恢复实证。','保留16完整要求，包括MAIN1080p29.97 HEVC42010约16Mbps/exact30单列、实际文件音画长录、同机备份/访问归还/逆写冷启动；未具备首刷条件。','195仅主机root01仍未具体批准，不启动或重问；不新增相机缓存/认证/上传/目标执行或固件写入。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert old[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3实际加载上下文与公开恢复复查](<'+rel+'/README.md>)：13原指令/6切片/225记录绑定，常规APP/INFRA线程加载不证明候选主线程可达；三公开HEAD重核，新QEMU提交仅65行UI研究文档、SD恢复全程仍待实测。真实入口/同机备份/独立AP恢复及首刷仍缺，无设备/root。'
assert ib.decode().count(marker)==1 and entry not in ib.decode();ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode();after=enc(new)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
for dst,data in [(canonical,after),(index,ia)]:
 tmp=H/('.'+dst.name+'.tmp')
 with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,dst)
members=[]
for p in sorted(H.rglob('*')):
 s=p.lstat()
 if stat.S_ISDIR(s.st_mode):continue
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink();members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage228-real-entrypoint-audit-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
