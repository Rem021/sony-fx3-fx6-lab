"""Register the tested own-source boot candidate without expanding authority."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess,zipfile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
P=B/'stage214-AP-boot-read-transfer-and-capacity'
PREV='822a2d7ab12816e10bfe8dba942ebc63ef11b6fed9979920446c539f827604ae'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
ZIP04='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
ZIP05='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):(H/n).open('x').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
assert digest(P/'final-receipt.json')==PREV
prev=json.loads((P/'final-receipt.json').read_text());assert len(prev['files'])==63
for row in prev['files']:
    p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==row['bytes'] and digest(p)==row['sha256']
release=json.loads((H/'release-receipt.json').read_text());archive=R/release['archive']
assert len(release['files'])==23 and archive.stat().st_size==84536 and digest(archive)==ZIP05==release['archive_sha256']
assert json.loads((T/'releases/release.json').read_text())==release
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist())==23
    for row in release['files']:
        p=T/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
        assert sha256(z.read('fx3-recovery-adapter-0.5.0/'+row['path'])).hexdigest()==row['sha256']
assert release['source_only'] and not release['hardware_validated'] and not release['flashable'] and not release['independent_recovery_proven']
assert digest(T/'releases/fx3-recovery-adapter-0.4.0.zip')==ZIP04
old_release=json.loads((T/'releases/fx3-recovery-adapter-0.4.0.json').read_text())
for name in ('native/fx3_p1_reader.c','native/entry.S'):
    assert digest(T/name)==next(x['sha256'] for x in old_release['files'] if x['path']==name)
counts={'boot-first':11,'legacy-adapter':13,'legacy-capture':14,'legacy-worker':11,'legacy-elflink':9}
results={};test_rows=[]
for name,count in counts.items():
    p=H/'runs'/name/'test-receipt/results.json';j=json.loads(p.read_text());results[name]=j
    assert j['status'].startswith('PASS') and j['tests_run']==count and j['failures']==j['errors']==0
    test_rows.append(dict(suite=name,tests=count,receipt=str(p.relative_to(R)),sha256=digest(p)))
assert sum(counts.values())==58
boot=results['boot-first'];assert len(boot['cases'])==74 and len(boot['guests'])==3
assert all(not x['errors'] for x in boot['cases'])
assert [len(x['source_reads']) for x in boot['guests']]==[2,126,0]
assert [x['worker_exitcode'] for x in boot['guests']]==[0,0,14]
assert all(x['AArch64_machine_code_executed'] and not x['real_Linux_or_Sony_kernel_executed'] for x in boot['guests'])
assert digest(T/'tests/test_boot_worker.py')==boot['test_source_sha256']
assert digest(T/'native/fx3_boot_reader.c')==boot['worker_source_sha256']=='06af135abf4e04ccb7cbc0727d4275ed4faf892fce6175f394a93aa7ce0aaaf5'
assert len(boot['elf_build']['relocations'])==97
assert digest(H/'runs/boot-first/built/worker.elf')==digest(H/'runs/boot-first/cli-built/worker.elf')==digest(H/'build-first/worker.elf')=='6e1fe8e803c3e900e25b1e7046dbf8e705ea66a8e8ccee268dcd15070d0acd70'
for name in ('max-assembled','cli-max'):
    assert digest(H/'runs/boot-first'/name/'source.boot1')==boot['synthetic_source_sha256']
minimum=H/'runs/boot-first/min-assembled/source.boot0';assert minimum.stat().st_size==131072
for path,size,sha in boot['public_reference_file_profile']:
    p=B/'stage213-AP-eMMC-boot-asset-search/originals/current-p3-initrd'/path.lstrip('/')
    assert p.stat().st_size==size and digest(p)==sha
old_p1=json.loads((B/'stage188-static-ELF-link-and-explicit-entry/runs/link-tests-final/test-receipt/results.json').read_text())['linked_ELF_sha256']
assert results['legacy-elflink']['linked_ELF_sha256']==old_p1=='c3a7b81d95d1d537d1f97bdab9eb0117f55bdeaee9b232d1f561d3d58040e2fd'
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for path in list(H.glob('*.py'))+list((T/'fx3_recovery').glob('*.py'))+[T/'tests/test_boot_worker.py']:
    ast.parse(path.read_text(),filename=str(path))
for page in [H/'README.md',T/'README.md',T/'native/README.md']:
    for link in re.findall(r'\]\(([^)]+)\)',page.read_text()):
        if '://' not in link and link not in ('final-receipt.json','verification-receipt.json'):
            assert (page.parent/link.strip('<>')).resolve().exists(),(page,link)
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-recheck.json').read_text())
assert native['goal']['status']=='blocked' and len(old['requirements'])==16
assert not old['goal_complete'] and not old['persistent_write_release'] and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('verification-receipt.json',dict(schema='fx3-stage215-offline-boot-worker-verification-v1',created_utc=now,
 status='PASS_58_LOCAL_TESTS_SOURCE_ONLY_CANDIDATE',previous_manifest_sha256=PREV,previous_members_reverified=63,
 suites=test_rows,tests_passed=58,new_boot_tests=11,boot_fixture_cases=74,boot_ARM64_guests=3,
 boot_ARM64_source_reads=[2,126,0],real_Linux_or_Sony_kernel_executed=False,Sony_code_executed=False,
 own_ARM64_code_executed=True,linked_ELF_bytes=20480,boot_relocations=97,
 linked_boot_ELF_sha256=digest(H/'runs/boot-first/built/worker.elf'),old_p1_ELF_sha256_unchanged=old_p1,
 minimum_synthetic_bytes=131072,maximum_synthetic_bytes=33423360,maximum_window_counts=[128,128,128,126],
 module_fingerprint_sha_independently_checked=True,current_body_geometry_measured=False,
 source_package_sha256=ZIP05,source_package_files=23,source_package_no_binary_or_firmware=True,
 release04_unchanged=True,old_p1_source_and_entry_unchanged=True,
 root01_bundle_unchanged=True,root01_job_absent=True,all16_requirements_and_authorizations_unchanged=True,
 actual_same_body_backup_or_restore_tested=False,actual_read_view_or_access_restoration_proven=False,
 camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False,
 test_timing_note='Boot suite ran after final executable code/CLI changes. Subsequent init version-only metadata and prose changes do not change candidate behavior; legacy47 suites ran with final version metadata. Exploratory pre-name-length-fix object is preserved but not accepted or released.'))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='blocked',
 goal_manager_status_last_observed='blocked',native_goal_state_not_modified=True,
 research_activity='Implemented0.5 own boot0/boot1 bounded C reader and independent wire, fixed ARM64 entry, pinned file-profile gate rejecting updater marker, dynamic1..255*128KiB geometry and local decoder/assembler/build CLI.11new+47legacy tests pass;74boot fixture cases,3own ARM64 fake-kernel runs2/126/0reads.23file source-only release;oldp1 ELF and0.4 unchanged. No camera/root/USB operations,16requirements and195pending unchanged;actual origin/loaded driver/view/access restoration and independent rescue unverified.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-recheck.json',observed_utc=native['observed_utc'],status='blocked',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='继续',receipt=REL+'/manual-continuation-receipt.json',classification='progress',native_status_remains='blocked',fresh_blocked_audit=True,same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('215将B0/B1受限读取接成0.5源码：主系统3模块文件SHA门及IAMUPDATER拒绝、动态容量、独立128/256B协议、窗口请求绑定、单次读取与失败拒绝、本地组装和构建CLI。11新+47旧=58项通过，74夹具案例；当前自写ARM64机器码3组2/126/0块，内核/设备仍假。旧p1ELF和0.4不变；无USB/root/设备操作，195待答及16要求保留，实际备份/视图/归还/独立恢复未验。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',release=release['archive'],release_sha256=ZIP05,
 source_change_inventory=REL+'/source-change-inventory.json',boot_tests=REL+'/runs/boot-first/test-receipt/results.json',
 source_candidate='outputs/fx3-recovery-adapter/native/fx3_boot_reader.c',protocol='outputs/fx3-recovery-adapter/fx3_recovery/boot_worker.py',
 scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',tests_passed=58,
 own_ARM64_guest_execution=True,Sony_code_or_real_Linux_kernel_execution=False,camera_USB_or_root_operations=0)
new['latest_stage_evidence']['stage215_AP_boot_capture_worker_candidate']=ev
new['recovery_AP_boot_capture_worker_candidate']={**ev,'version':'0.5.0','local_source_build_only':True,'fixed_targets':['boot0','boot1'],
 'geometry_formula':'reported1..255*128KiB, proc/ioctl agreement, later windows bound','actual_body_geometry_bytes':None,
 'module_file_profile_is_loaded_driver_or_body_attestation':False,'updater_environment_marker_rejected':True,
 'boot_worker_ELF_sha256':digest(H/'runs/boot-first/built/worker.elf'),'boot_worker_relocations':97,
 'camera_transfer_or_launch_backend':False,'actual_body_origin_or_read_view_verified':False,
 'hardware_partition_access_restoration_proven':False,'independent_boot_or_restore_proven':False}
new['next_safe_offline_actions']=[
 '195仅主机root01原具体问题待答；不将继续当批准，不启动或重问，不扩大相机权限。',
 '215已有boot0/boot1源码候选和本地解码、58项检查及0.5源码包；围绕可信执行/退出收据、现有原生owner与启动链继续适配。先验证不读取源分区的本地主机方案，不提供上传/设备启动命令，不以模块文件SHA代替已加载驱动/机身身份。',
 '追同机AP启动区读出视图、完整配置与安装p1身份的证据获取方案；容量不预填，读取可能切硬件访问选择或panic，阻塞保持UNKNOWN，未证归还不能自动重试或假称已恢复。',
 '保留独立AP入口、同机完整备份、逆写/冷启动/故障恢复及全部16要求和真实MAIN1080p29.97 HEVC长录验收缺口；本地主机与ARM64假内核通过不充真机恢复或刷入放行。']
for k in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[k]==old[k],k
for k in old['latest_stage_evidence']:assert new['latest_stage_evidence'][k]==old['latest_stage_evidence'][k]
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3启动区采集工作器候选0.5](<'+REL+'/README.md>)：B0/B1动态容量及环境过滤已接入C/独立协议/本地组装，11新+47旧=58项离线测试通过；23文件源码包，旧p1/0.4保留。实际备份、访问归还及独立救砖未验；无设备/root操作，195待答。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[];excluded=[]
for p in sorted(H.rglob('*')):
    s=p.lstat()
    if stat.S_ISDIR(s.st_mode):continue
    if not stat.S_ISREG(s.st_mode):
        excluded.append(dict(path=str(p.relative_to(R)),reason='adversarial non-regular fixture not followed',mode=oct(s.st_mode)));continue
    members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=digest(p)))
put('final-receipt.json',dict(schema='fx3-stage215-boot-worker-source-candidate-v1',created_utc=now,
 previous_manifest_sha256=PREV,previous_members_reverified=63,files=members,member_count=len(members),excluded=excluded,
 external_immutable_release=dict(path=release['archive'],sha256=ZIP05,bytes=84536),
 source_working_tree_mutable_not_manifest_members=True,source_snapshot_in_verified_release_archive=True,
 mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),
 tests_passed=58,own_ARM64_guest_execution=True,Sony_code_or_real_Linux_kernel_execution=False,
 new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,new_approval_granted=False,
 native_goal_observed='blocked',manual_continue_request_processed=True,native_goal_status_changed_by_assistant=False,
 goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),excluded=len(excluded),tests_passed=58,
 release05_sha256=ZIP05,requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
