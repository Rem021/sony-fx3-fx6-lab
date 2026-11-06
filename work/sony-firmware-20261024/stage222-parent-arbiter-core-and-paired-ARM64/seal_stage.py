"""Verify and register paired own ARM64 parent/worker evidence, not a release."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage221-private-IPC-entry-gate';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='16aa8683271aee78e949a3b2bcbe6811490ad632677efe279916d7d79f9d8d01'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
PARENT='5a9ab04e92e06dd5fbddbff0c95e1736ac4c0850a8ad9a346a01669104e0eb39'
CHILD='23327fd5c43ecf44858f0705edc30db1ed795d1bc2272bf75bbeaf1ae8e8b3a3'
UNSAFE='eda3c4bbd8b3917d5e873b1b57664662d7fdac324ebe81d61214b02898818538'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def encode(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,value):(H/name).open('xb').write(encode(value))
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==1353
for row in prior['files']:
    p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256']
sys.path.insert(0,str(H));import dynparent as D
r=json.loads((H/'runs-final/receipt/results.json').read_text());build=r['build']
assert r['status']=='PASS' and r['tests_run']==15 and r['failures']==r['errors']==0
assert len(r['cases'])==38 and len(r['parent_guests'])==34 and r['all_fixture_threads_terminal']
for name,digest in r['source_hashes'].items():assert sha(H/name)==digest
for name,digest in build['source_pins'].items():assert sha(H/name)==digest==D.SOURCE_PINS[name]
assert build['sha256']==sha(H/'runs-final/built/parent-module.so')==sha(H/'runs-final/reproducible/parent-module.so')==PARENT
assert build['bytes']==262936 and len(build['link_relocations'])==236 and len(build['runtime_relocations'])==1
assert sum(x['kind']=='LDST32_ABS_LO12_NC' for x in build['link_relocations'])==18
assert sha(P/'runs-final-v2/built/boot-module.so')==CHILD
fmt=D.inspect((H/'runs-final/built/parent-module.so').read_bytes());assert set(fmt['exports'])=={'fx3_arbiter_submit','fx3_arbiter_poll'}
assert not fmt['has_DT_NEEDED_or_imports'] and not fmt['actual_Sony_loader_acceptance_verified']
assert b'/dev/' not in (H/'runs-final/built/parent-module.so').read_bytes()
assert not build['source_initializer_calls_worker_or_syscall'] and not build['actual_child_launch_or_wait4_verified']
assert all(not p['errors'] and p['first_init_syscalls']==0 for p in r['parent_guests'])
assert r['own_parent_and_worker_ARM64_executed'] and r['all_Linux_IPC_credentials_wait4_processes_and_clock_are_fixtures']
assert not r['actual_fork_exec_loader_or_Sony_code_executed'] and not r['actual_target_root_domain_or_global_exclusion_verified']
assert r['new_camera_operations']==0 and not r['flashable'] and not r['hardware_validated'] and not r['independent_recovery_proven']
cases={c['name']:c for c in r['cases']};assert len(cases)==38
assert sum(c['child_return'] is not None for c in r['cases'])==27
assert all(not c['child_errors'] and not c['parent_errors'] for c in r['cases'])
assert [cases['full-'+str(i)]['source_reads'] for i in range(4)]==[128,128,128,126]
assert all(cases['full-'+str(i)]['state']==0 for i in range(4))
assert cases['blocked']['state']==2 and cases['blocked']['child_return']==23 and cases['blocked']['source_reads']==1
assert cases['other-owner']['state']==2 and cases['other-owner']['parent_packets']==[]
assert cases['normal']['state']==cases['normal-next']['state']==cases['other-valid-PIDs']['state']==0
for name in ('no-done','duplicate-done','child-close','parent-close','chunk-body','chunk-index','manifest-binding','request-binding','output-drift','output-close','output-late'):
    c=cases[name];assert c['state']==2 and c['source_reads']==2
    if name!='child-close':assert c['child_return']==0 and c['exit_status']==0
assert cases['child-close']['child_return']==58
assert cases['late-owner']['state']==2 and cases['late-owner']['exit_status']==0
for name in ('message-pid','message-uid','rights'):
    assert cases[name]['state']==2 and cases[name]['source_reads']==0 and cases[name]['parent_packets']==[1]
assert cases['rights']['extra_received_FDs']==cases['rights']['extra_closed_FDs']==[360,361]
for fault in ('record-short','record-sync','foreign-child','wait-error'):
    assert cases[fault]['state']==cases[fault+'-restart']['state']==2
    assert cases[fault]['parent_packets']==cases[fault+'-restart']['parent_packets']==[]
    file=H/'runs-final'/(fault+'-global')/'owner-session.pending'
    assert file.stat().st_size==(255 if fault=='record-short' else 256)
    if fault in ('foreign-child','wait-error'):assert cases[fault]['waits'][0]['returned']==(-10 if fault=='foreign-child' else -4)
race=[cases['race-first'],cases['race-second']];assert sorted(c['state'] for c in race)==[0,2]
assert sorted(c['source_reads'] for c in race)==[0,2]
assert cases['completed-owner']['state']==0 and cases['completed-restart']['state']==2
assembly=json.loads((H/'runs-final/assembled/complete.json').read_text())
assert assembly['bytes']==33423360 and len(assembly['windows'])==4 and assembly['sha256']==sha(H/'runs-final/assembled/source.boot1')=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
assert not assembly['hardware_validated'] and not assembly['same_body_origin_verified']
first=json.loads((H/'runs-first/receipt/results.json').read_text());mid=json.loads((H/'runs-second/receipt/results.json').read_text())
assert first['status']=='FAIL' and first['failures']==9 and first['errors']==0
for name in ('paired_model.py','test_paired_arbiter.py'):assert sha(H/('first-tested-'+name))==first['source_hashes'][name]
assert not (H/'runs-first/record-short-global').exists(),'initial apparent refusal did not reach fault branch'
assert mid['status']=='PASS' and mid['tests_run']==12 and mid['build']['sha256']==UNSAFE
for name in ('parent_module.c','dynparent.py','paired_model.py','test_paired_arbiter.py'):assert sha(H/('twelve-test-passed-'+name))==mid['source_hashes'][name]
gap=json.loads((H/'output-validation-gap/receipt/gap.json').read_text())
assert gap['parent_module_sha256']==sha(H/'output-validation-gap/built/parent-module.so')==UNSAFE and gap['parent_state_after_corrupt_chunk']==0 and gap['independent_decoder_rejected'] and not gap['readiness_pass']
probes=[]
for folder,expected,digest in [('probe-old',0,UNSAFE),('probe-new',2,PARENT)]:
    p=json.loads((H/folder/'receipt/probe.json').read_text());assert p['parent_module_sha256']==digest and p['parent_state']==expected
    assert p['child_return']==p['exit_status']==0 and p['independent_decoder_rejected'] and p['all_fixture_threads_terminal'] and not p['readiness_pass'] and p['new_camera_operations']==0
    assert p['probe_source_sha256']==sha(H/'probe_output_validation.py') and p['model_source_sha256']==sha(H/'paired_model.py');probes.append(p)
derived=json.loads((H/'core-source-derivation.json').read_text());src=(R/derived['source']).read_bytes();assert sha256(src).hexdigest()==derived['source_sha256']
pieces=[]
for row in derived['ranges']:
    piece=src[row['offset']:row['offset']+row['bytes']];assert sha256(piece).hexdigest()==row['sha256'];pieces.append(piece)
assert b''.join(pieces)==(H/'core_support.inc').read_bytes() and sha(H/'core_support.inc')==derived['derived_sha256']
transport=json.loads((H/'transport-derivation.json').read_text());src=(R/transport['source']).read_bytes();assert sha256(src).hexdigest()==transport['source_sha256'];raw=src[:transport['source_prefix_bytes']]
for change in transport['ordered_changes']:
    before=change['before'].encode();after=change['after'].encode();at=change['offset_in_previous'];assert raw[at:at+len(before)]==before;raw=raw[:at]+after+raw[at+len(before):]
assert raw==(H/'parent_ipc.inc').read_bytes() and sha(H/'parent_ipc.inc')==transport['derived_sha256']
for file in ('source-reference-capture.json','AArch64-ABI-source-capture.json','wait-UAPI-source-capture.json'):
    cap=json.loads((H/file).read_text());assert cap.get('curl_returncode',cap.get('returncode'))==0
    assert (H/cap['path']).stat().st_size==cap['bytes'] and sha(H/cap['path'])==cap['sha256']
abi=json.loads((H/'kernel-and-link-ABI-review.json').read_text());assert abi['wait4_number']==260 and abi['wait4_argument_count']==4 and abi['wait4_nonblocking_option']==1
assert sha(H/'source-reference/aaelf64.rst')==abi['Arm_relocation_source_sha256']
assert 'LDST32' in (H/'source-reference/aaelf64.rst').read_text().splitlines()[abi['Arm_relocation_line']-1]
assert sha((H/abi['wait4_number_source']).resolve())==abi['wait4_number_source_sha256']
assert b'0x00000001' in (H/'source-reference/wait.h').read_bytes()
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
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16
assert old['latest_stage']==P.name and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
verification=dict(schema='fx3-stage222-own-parent-worker-ARM64-verification-v1',created_utc=now,
    status='PASS_PAIRED_MODEL_OUTPUT_RELEASE_GAP_FIXED_NO_TARGET_LAUNCH_OR_RECOVERY',
    previous_manifest_sha256=PREV,previous_members_reverified=1353,parent_module_sha256=PARENT,child_module_sha256_unchanged=CHILD,
    tests_passed=15,scenarios=38,parent_ARM64_instances=34,child_explicit_invocations=27,child_initialization_only=11,
    code_link_relocations=236,LDST32_code_relocations=18,runtime_initialization_relocations=1,
    nominal_paired_model_fixed_namespace_serialization_verified=True,private_DONE_child_exit_and_RAM_output_reread_required=True,
    old_output_release_gap_reproduced=True,old_new_same_probe_comparison=probes,public_record_or_dead_PID_can_release=False,
    all_model_threads_terminal=True,initial_invalid_fixture_and_unsafe_intermediate_sources_preserved=True,
    actual_fork_exec_inherited_channel_loader_or_explicit_dispatch_implemented=False,
    actual_Linux_credentials_wait4_clock_root_or_global_exclusion_verified=False,all_native_callers_forced_through_parent_core=False,
    own_parent_and_worker_ARM64_executed=True,Sony_or_Linux_kernel_or_native_loader_executed=False,
    parent_only_rereads_RAM_not_source_device=True,actual_camera_origin_plaintext_or_hardware_access_restore_verified=False,
    formal_release04_and05_and23_sources_unchanged=True,root01_bundle_and_absent_job_unchanged=True,
    all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Own ARM64 parent submit/poll core now drives unchanged221worker GRANT/READY/GO/DONE through shared fake Linux model. Fixed root RAM session mkdir+pending file, private live state, reference im self guard, message child credentials and wait4(WNOHANG) gate sequential jobs; no persisted completion/PID-loss reclaim. Reproduced intermediate DONE0+exit0 releasing corrupt output, then added RAM request/manifest/chunk reread, stable metadata, CRC/range/close/deadline verification before release.15tests/38scenarios,34parentinstances/27childentries,4windows33423360synthetic bytes; same old/new binary probe shows0unsafe vs2held. Local restricted LDST32 linking only; formal linker unchanged. Actual launcher/fork/exec/FD inheritance/dispatch, root IPC/global domain and camera backup/recovery unverified.16requirements,195pending,0.4/0.5 unchanged; no camera/root/Sony code execution.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active persistent goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('222自写ARM64父端与221子端真正按320B协议双端联测：固定RAM会话独占/私有状态、逐消息子凭据、wait4非阻塞观察共同串行；阻塞/双实例/并发争抢/完成与退出缺项/错误凭据均保持占用。旧C初版输出损坏仍释放已复现，新增请求/清单/数据块复读、CRC/身份/期限/关闭核对；同一旧/新二进制探针对照0错误释放→2保持UNKNOWN。最终15检查/38场景、34父端/27子端进入、四窗口人工源完整组装。局部新增285重定位且正式elflink不变；真实启动/继承/分派/加载/rootIPC/备份恢复未证，16要求/195/0.4/0.5保留，无设备/root。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/parent_module.c',transport=REL+'/parent_ipc.inc',output_validation=REL+'/output_validate.inc',
    builder=REL+'/dynparent.py',model=REL+'/paired_model.py',tests=REL+'/runs-final/receipt/results.json',build=REL+'/runs-final/built/build.json',
    old_gap=REL+'/output-validation-gap/receipt/gap.json',old_probe=REL+'/probe-old/receipt/probe.json',new_probe=REL+'/probe-new/receipt/probe.json',
    scope=REL+'/implementation-review.json',ABI=REL+'/kernel-and-link-ABI-review.json',parent_module_sha256=PARENT,child_module_sha256_unchanged=CHILD,
    nominal_paired_model_exclusion_verified=True,actual_target_launcher_or_root_global_exclusion_verified=False,new_device_operations=0)
new['latest_stage_evidence']['stage222_parent_arbiter_paired_ARM64']=ev
new['recovery_parent_arbiter_core_and_paired_model']={**ev,'tests_passed':15,'scenarios':38,'parent_ARM64_instances':34,'child_explicit_invocations':27,
    'old_output_release_gap_reproduced_and_fixed_in_model':True,'same_live_parent_sequential_full_capture_preserved':True,
    'persisted_record_or_PID_disappearance_can_resume_owner':False,'actual_fork_exec_FD_inheritance_or_dispatch_implemented':False,
    'all_native_callers_enforced_through_core':False,'same_body_backup_restore_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01具体问题待答；不从active/继续推导批准，不启动或重问，不扩大相机权限。',
    '222父端C核心已在双端ARM64模型中串行221子端并要求退出和RAM输出复读；下一项补同一受控启动链：实际创建子进程/继承私有FD/加载与显式分派入口/退出码传播，先离线自写代码和假内核验证。不得把模型注册的child或预建队列当成真实fork/exec证据。',
    '父端按参考im上下文过滤，子端仍要求im父身份和新13B shell空操作合同；若改独立keeper须同步修订身份/程序合同。固定资源目录需真实root/tmpfs域验证，实际所有调用是否走核心、完整加载代码及用户批准不能由PID/凭据/SHA或会话记录推断。',
    '保留全部16要求、同机健康boot/p1/完整配置、实际数据视图/访问归还、独立AP入口、逆写/冷启动及MAIN1080p29.97 HEVC/长录。当前窗口CRC和模型软件归还不充硬件恢复、完整备份或首刷放行。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=encode(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3父端C监管与双端ARM64联测](<'+REL+'/README.md>)：15检查/38场景通过，固定会话、私有完成、子退出和RAM复读共同放行；旧/新二进制对照修复损坏输出仍释放的问题，四窗口人工源完整组装。真实启动/继承/加载/root域/恢复未验，16要求/195/0.5保留，无设备/root。'
assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent head change'
put('verification-receipt.json',verification);(H/'goal-status-after.json').open('xb').write(after)
(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[]
for p in sorted(H.rglob('*')):
    s=p.lstat()
    if stat.S_ISDIR(s.st_mode):continue
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink();members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage222-parent-responding-core-and-paired-ARM64-v1',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=1353,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
    tests_passed=15,scenarios=38,parent_ARM64_instances=34,child_explicit_invocations=27,parent_module_sha256=PARENT,child_module_sha256_unchanged=CHILD,
    nominal_paired_model_exclusion_verified=True,old_output_release_gap_fixed_in_model=True,actual_launcher_or_root_global_domain_verified=False,
    new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,native_goal_observed='active',native_goal_status_changed_by_assistant=False,
    goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=15,scenarios=38,
    parent_ARM64_instances=34,child_explicit_invocations=27,parent_module_sha256=PARENT,actual_target_launch_verified=False,
    requirements_unchanged=16,new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
