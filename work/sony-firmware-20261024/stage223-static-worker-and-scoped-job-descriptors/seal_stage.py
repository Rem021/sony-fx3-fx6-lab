"""Seal own static worker model evidence; does not launch or release a device job."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,struct,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage222-parent-arbiter-core-and-paired-ARM64';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='d77605f5d0ac8f5bedc4cbfd546c399b7ead6c62c6033cfbc4d06a763995cd10'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
IMAGE='e40d068d43123f8f86eba5c46a1428e02e5e16c84df2211174c578d4cd273d7d'
PARENT='5a9ab04e92e06dd5fbddbff0c95e1736ac4c0850a8ad9a346a01669104e0eb39'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==1391
for row in prior['files']:
    p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
sys.path.insert(0,str(H));import static_build as S
r=json.loads((H/'runs-import-fixed/receipt/results.json').read_text());build=r['build']
assert r['status']=='PASS' and r['tests_run']==8 and r['failures']==r['errors']==0 and not r['failure_details']
assert len(r['cases'])==25 and r['all_model_threads_terminal']
for n,d in r['source_hashes'].items():assert sha(H/n)==d,n
assert build['source_pins']==S.SOURCE_PINS==json.loads((H/'active-source-pins.json').read_text())
for n,d in build['source_pins'].items():assert sha(H/n)==d
raw=(H/'runs-import-fixed/built/worker.elf').read_bytes()
assert sha256(raw).hexdigest()==sha(H/'runs-import-fixed/reproducible/worker.elf')==sha(H/'build-linked/worker.elf')==IMAGE
assert build['sha256']==IMAGE and build['bytes']==len(raw)==262144
segments=S.read_executable(raw);assert segments==build['segments'] and build['entry']==struct.unpack_from('<Q',raw,24)[0]
entry=build['entry']-S.BASE;words=struct.unpack_from('<IIII',raw,entry)
assert words[0]&0xfc000000==0x94000000 and words[1:]==(0xd2800ba8,0xd4000001,0x14000000)
assert build['segment_alignment']==65536 and build['ADRP_instruction_page']==4096
assert not build['runtime_loader_or_imports'] and not build['shared_library_or_constructor_or_Sony_loader_required']
assert not build['actual_target_exec_or_inherited_FDs_verified'] and not build['parent_has_pinned_image_before_exec']
assert sum(x['kind']=='LDST32_ABS_LO12_NC' for x in build['relocations'])==2
for word,target in [(0xb9000000,0x1234),(0xb9400001,0x1ffc)]:
    patched=S.relocate(word,285,0x400000,target);assert ((patched>>10)&0xfff)*4==target&0xfff
for word,target in [(0xf9000000,0x1234),(0xb9000000,0x1235)]:
    try:S.relocate(word,285,0x400000,target)
    except Exception:pass
    else:raise AssertionError('unsupported LDST32 form accepted')
assert sha(P/'runs-final/built/parent-module.so')==PARENT
assert (H/'inner_boot_reader.c').read_bytes()==(B/'stage221-private-IPC-entry-gate/inner_boot_reader.c').read_bytes()
assert (H/'handoff_impl.inc').read_bytes()==(B/'stage221-private-IPC-entry-gate/handoff_impl.inc').read_bytes()
ipc=(B/'stage221-private-IPC-entry-gate/ipc_gate.inc').read_text()
assert (H/'ipc_gate.inc').read_text()==ipc.replace('IPC_FD=198, ','').replace('struct ipc_context {int owned;u8 hand[256];};','struct ipc_context {int owned;long fd;u8 hand[256];};').replace('IPC_FD,','gate->fd,')
cases={c['name']:c for c in r['cases']};assert len(cases)==25
assert all(c['first_syscall']==172 and c['last_syscall']==93 and c['entry']==build['entry'] and c['reaped'] for c in r['cases'])
success=['normal','roles-0','roles-1']+['full-'+str(i) for i in range(4)]
for n in success:
    c=cases[n];assert c['state']==c['child_exit']==0 and c['parent_packets']==[1,3] and c['child_packets']==[2,4]
    assert not c['kernel_exit_cleanup'] and c['explicit_role_closes']==c['inherited_roles']
assert cases['roles-0']['inherited_roles']==[0,1,2] and cases['roles-1']['inherited_roles']==[181,182,183]
assert [cases['full-'+str(i)]['source_reads'] for i in range(4)]==[128,128,128,126]
for n,c in cases.items():
    if n not in success:assert c['state']==2
    if n.startswith('argv-') or n in ('image-mismatch','image-uid','image-mode','image-writable','cloexec','wrong-directory','replay-window'):assert c['source_reads']==0 and c['parent_packets']==[1]
assert cases['replay-window']['child_exit']==51
for n,code in [('image-close',46),('directory-close',46),('ipc-close',58)]:assert cases[n]['child_exit']==code and cases[n]['source_reads']==2
assert cases['bad-output']['child_exit']==0 and cases['bad-output']['child_packets']==[2,4] and cases['bad-output']['source_reads']==2
assembly=json.loads((H/'runs-import-fixed/assembled/complete.json').read_text())
assert assembly['bytes']==33423360 and len(assembly['windows'])==4 and assembly['sha256']==sha(H/'runs-import-fixed/assembled/source.boot1')=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
assert not assembly['hardware_validated'] and not assembly['same_body_origin_verified']
assert r['own_static_ELF_start_to_exit_executed'] and not r['Sony_BusyBox_glibc_or_Linux_kernel_executed']
assert not r['actual_fork_exec_descriptor_inheritance_or_kernel_ELF_acceptance_verified'] and not r['parent_image_hash_preexec_enforcement_implemented']
assert r['new_camera_operations']==0 and not r['flashable'] and not r['hardware_validated'] and not r['independent_recovery_proven']
first=json.loads((H/'runs-first/receipt/results.json').read_text());assert first['status']=='FAIL' and first['failures']==4 and first['errors']==1
for n,d in first['source_hashes'].items():assert sha(H/'runs-first/source-snapshot'/n)==d
for cap in json.loads((H/'web-source-capture.json').read_text())+[json.loads((H/'fcntl-UAPI-source-capture.json').read_text())]:
    assert cap['returncode']==0 and (H/cap['path']).stat().st_size==cap['bytes'] and sha(H/cap['path'])==cap['sha256']
u=B/'stage221-private-IPC-entry-gate/kernel-reference/unistd.h';ul=u.read_text().splitlines();f=H/'source-reference/fcntl.h';fl=f.read_text().splitlines()
expected=[(u,ul,94,'#define __NR3264_fcntl 25'),(u,ul,296,'#define __NR_exit 93'),(f,fl,100,'#define F_GETFD\t\t1'),(f,fl,102,'#define F_GETFL\t\t3'),(f,fl,161,'#define FD_CLOEXEC\t1'),(f,fl,84,'#define O_PATH\t\t010000000')]
for p,lines,line,prefix in expected:assert lines[line-1].startswith(prefix)
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text());assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(T/'fx3_recovery/elflink.py')==json.loads((H/'builder-source-derivation.json').read_text())['source_sha256']
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link not in ('implementation-review.json','kernel-and-link-ABI-review.json','verification-receipt.json','final-receipt.json'):assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());status=native['goal']['status']
assert status=='blocked' and old['latest_stage']==P.name and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
scope=dict(scope='own static ARM64 child _start to exit93 and unchanged222parent on Mac with fake Linux syscalls; ordinary Mac fixture files only',
    own_static_child_has_no_Sony_loader_constructor_or_glibc_dependency=True,own_static_child_start_to_exit_executed=True,
    nominal_parent_worker_private_protocol_interoperates=True,fixed_global_nonce_and_window_namespace_preserved=True,
    inherited_descriptor_arguments_are_only_modeled=True,image_backing_inode_association_implemented=True,
    parent_preexec_complete_image_SHA_pin_implemented=False,actual_fork_exec_or_descriptor_inheritance_implemented=False,
    actual_Linux_ELF_acceptance_mount_exec_policy_root_credentials_or_hardware_verified=False,
    controlled_input_staging_and_other_FD_whitelist_implemented=False,private_job_directory_or_IPC_v2_active=False,
    own_ARM64_executed=True,Sony_BusyBox_glibc_or_Linux_kernel_executed=False,all_model_threads_terminal=True,
    tests_passed=8,scenarios=25,formal_23_sources_and_release04_05_unchanged=True,
    new_camera_USB_cached_queries_root_auth_upload_execution_or_persistent_writes=0,
    stage195_root01_still_pending=True,all16_requirements_unchanged=True,
    same_body_boot_backup_data_view_hardware_return_restore_coldboot_or_independent_AP_rescue_proven=False,
    native_goal_status_observed=status,native_goal_status_changed_by_assistant=False,meaningful_safe_offline_work_remains=True,
    goal_complete=False,persistent_write_release=False)
abi=dict(schema='fx3-stage223-static-worker-kernel-and-link-ABI-v1',primary_sources_rechecked=True,
    ABI_constants=[dict(path=str(p.relative_to(R)),sha256=sha(p),line=line,checked_prefix=prefix) for p,lines,line,prefix in expected],
    fcntl_number=25,exit_number=93,F_GETFD=1,F_GETFL=3,FD_CLOEXEC=1,O_PATH=0x200000,
    segment_alignment=65536,ADRP_instruction_page=4096,LDST32_relocations=2,local_LDST32_valid_and_invalid_forms_checked=True,
    ELF_start_words=[hex(x) for x in words],formal_linker_unchanged=True,actual_kernel_execution=False)
verification=dict(schema='fx3-stage223-own-static-start-and-parent-verification-v1',created_utc=now,
    status='PASS_OWN_STATIC_ENTRY_AND_PAIRED_MODEL_NO_ACTUAL_EXEC_OR_RECOVERY',previous_manifest_sha256=PREV,previous_members_reverified=1391,
    tests_passed=8,scenarios=25,static_worker_sha256=IMAGE,parent_module_sha256_unchanged=PARENT,
    static_worker_bytes=262144,reproducible_build=True,full_synthetic_bytes=33423360,
    four_window_source_sha256=assembly['sha256'],all_scenarios_reached_exit93=True,
    early_rejections_never_read_source=True,role_close_failures_and_corrupt_output_keep_parent_held=True,
    failed_first_model_and_source_snapshots_preserved=True,all_model_threads_terminal=True,
    actual_fork_exec_FD_inheritance_image_preexec_pin_or_kernel_acceptance_proven=False,
    formal23_sources_and_release04_05_and_root01_bundle_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
    new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status=status,goal_manager_status_last_observed=status,native_goal_state_not_modified=True,
    research_activity='Own static ARM64 worker now starts at _start and exits via93; no BusyBox/constructor/Sony loader/libc needed by child. Strict distinct inherited-role argv, image read-only/root0500 backing-inode association, fixed root FD cross-check and checked role closes. Original global nonce/window claims and IPCv1 preserved. Unchanged222parent interoperates;8tests/25scenarios passed,4windows33423360synthetic bytes assembled, close errors/replay/corruption held. Actual fork/exec/FD inheritance, complete image preexec pin, controlled staging, real kernel/root/mount policy/backup/rescue remain unverified.16requirements/195pending/formal0.4/0.5 preserved; no camera/root/Sony code execution. Native tracker read-only now reports blocked; manual user continuation makes safe offline progress, no native status change claimed.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status=status,source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='继续',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains=status,same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('223自写子端改独立静态ELF，_start至exit93与原222父端联测；三类动态角色FD参数、镜像后端inode/只读标志及根目录身份核对，原固定全局防重复和IPCv1保留。首轮模型漏导入导致失败已保留并修复，最终8检查/25场景与四窗口人工源组装通过。真实fork/exec/继承/镜像启动前SHA/输入暂存及机内恢复仍缺；16要求/195/正式包不变，无设备/root。原生目标新观察blocked，只登记不改状态；用户继续下仍有安全离线进展。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/worker.c',roles=REL+'/roles_and_image.inc',builder=REL+'/static_build.py',model=REL+'/static_model.py',tests=REL+'/runs-import-fixed/receipt/results.json',build=REL+'/runs-import-fixed/built/build.json',scope=REL+'/implementation-review.json',ABI=REL+'/kernel-and-link-ABI-review.json',static_worker_sha256=IMAGE,parent_module_sha256_unchanged=PARENT,tests_passed=8,scenarios=25,own_start_to_exit_executed=True,actual_exec_inheritance_or_preexec_image_pin_verified=False,new_device_operations=0)
new['latest_stage_evidence']['stage223_own_static_worker']=ev;new['recovery_own_static_worker_and_descriptor_contract']={**ev,'global_nonce_and_window_claims_preserved':True,'private_job_directory_or_IPCv2_active':False,'same_body_backup_restore_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01具体批准仍待答；不从继续/目标状态推导批准，不启动或重问，不扩大相机权限。',
    '223独立静态子端入口/退出及模型角色FD已通；补受控启动器的完整镜像SHA预核、进程创建、继承FD白名单、exec入口和退出传播，先仅自写ARM64与假内核验证。模型预建队列/child注册不充实际fork/exec。',
    '输入暂存必须在取得固定全局父会话后进行；若改私有任务目录，必须保留跨任务nonce/窗口防重复并绑定父子任务。机内im身份/root域/挂载执行策略/调用覆盖仍未证，不做remount或权限更改。',
    '保留16要求及MAIN1080p29.97 HEVC/exact30单列/长录；同机健康boot/p1/配置完整备份、真实数据视图与硬件访问归还、独立AP入口、逆写/冷启动均待验证，模型完成不充首刷放行。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=enc(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3独立静态工作程序与FD合同](<'+REL+'/README.md>)：8检查/25场景通过，自写_start至退出与原父端联测，动态角色FD/镜像inode关联，保留全局防重复及四窗口人工源组装。实际fork/exec/继承/启动前镜像SHA/机内恢复未验，16要求/195/正式包保留，无设备/root。'
assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent canonical head change'
put('implementation-review.json',scope);put('kernel-and-link-ABI-review.json',abi);put('verification-receipt.json',verification)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[]
for p in sorted(H.rglob('*')):
    s=p.lstat()
    if stat.S_ISDIR(s.st_mode):continue
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink();members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage223-static-worker-and-descriptor-contract-seal-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=1391,files=members,member_count=len(members),goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,tests_passed=8,scenarios=25,static_worker_sha256=IMAGE,parent_module_sha256_unchanged=PARENT,actual_fork_exec_inheritance_or_recovery_verified=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,native_goal_observed=status,native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=8,scenarios=25,static_worker_sha256=IMAGE,actual_target_launch_verified=False,requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
