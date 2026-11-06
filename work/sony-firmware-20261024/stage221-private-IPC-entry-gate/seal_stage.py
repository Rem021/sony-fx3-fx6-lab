"""Register own ARM64 inherited gate. Does not authorize target execution."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,subprocess,sys
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage220-live-session-global-arbiter-fixture';OLD=B/'stage219-bound-handoff-and-request-claims';T=R/'outputs/fx3-recovery-adapter';REL=str(H.relative_to(R))
PREV='d02b130cf91fd2bb27806f739f91c0c72a081f81a8c59e48cf7a1d2b0077837a'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
MODULE='23327fd5c43ecf44858f0705edc30db1ed795d1bc2272bf75bbeaf1ae8e8b3a3'
IPC='159dc5cb16b937f02f0399939831370c58242779d9bbc8a71d2bee6c1ee55725'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def encode(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,value):(H/name).open('xb').write(encode(value))
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and sha(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==2387
for row in prior['files']:
    p=R/row['path'];s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256']
sys.path.insert(0,str(H));import dynmodule as D
r=json.loads((H/'runs-final-v2/receipt/results.json').read_text());build=r['build']
assert r['status']=='PASS' and r['tests_run']==10 and r['failures']==r['errors']==0
assert len(r['cases'])==44 and len(r['guests'])==45
for name,digest in r['source_hashes'].items():assert sha(H/name)==digest
assert sha(H/'boot_module.c')==build['module_source_sha256']==D.MODULE_SHA
assert sha(H/'ipc_gate.inc')==build['ipc_gate_source_sha256']==IPC
assert sha(H/'handoff_impl.inc')==build['handoff_implementation_sha256']
assert sha(H/'inner_boot_reader.c')==build['inner_reader_sha256']==sha(OLD/'inner_boot_reader.c')
assert build['sha256']==sha(H/'runs-final-v2/built/boot-module.so')==sha(H/'runs-final-v2/reproducible/boot-module.so')==MODULE
assert build['bytes']==262936 and len(build['link_relocations'])==182 and len(build['runtime_relocations'])==1
assert build['private_inherited_datagram_gate_implemented'] and not build['global_target_keeper_integrated']
assert not build['cross_request_global_exclusion_implemented'] and not build['exclusive_request_attestation_verified']
assert not build['source_initializer_calls_worker_or_syscall'] and build['safe_child_cmdline_bytes']==13
fmt=D.inspect((H/'runs-final-v2/built/boot-module.so').read_bytes())
assert set(fmt['exports'])=={'fx3_boot_read_window','fx3_module_status'} and not fmt['actual_Sony_loader_acceptance_verified']
assert r['safe_shell_cmdline_bytes']==13 and bytes.fromhex(r['safe_shell_cmdline_hex'])==b'/bin/sh\0-c\0:\0'
assert r['own_ARM64_executed'] and not r['real_Linux_Sony_kernel_or_socket_credentials_verified'] and not r['live_global_target_keeper_integrated']
assert r['new_camera_operations']==0 and not r['flashable'] and not r['independent_recovery_proven']
assert all(not g['errors'] and g['calls'][0]['syscalls']==0 for g in r['guests'])
assert all(c['number'] not in (35,93,94,220,221) for g in r['guests'] for c in g['syscalls'])
ipc_trace=[c for g in r['guests'] for c in g['syscalls'] if c['number'] in (73,204,208,209,211,212)]
assert ipc_trace and all(len(c['args'])==6 for c in ipc_trace)
cases={c['name']:c for c in r['cases']};assert len(cases)==44
assert [cases['full-'+str(i)]['source_reads'] for i in range(4)]==[128,128,128,126]
assert all(cases['full-'+str(i)]['code']==0 for i in range(4))
assert [cases['normal-'+str(i)]['code'] for i in range(2)]==[0,0]
for name in ('missing-fd','fd-owner','not-socket','stream','not-unix','named','peer-pid','peer-uid','peer-gid','peer-size'):
    c=cases[name];assert c['code'] and not c['source_opens'] and not c['ipc_mutations'] and not c['ipc_closed']
after_source={'normal-0','normal-1','full-0','full-1','full-2','full-3','done-short','ipc-close','source-block'}
for name,c in cases.items():
    if name not in after_source:assert c['code']!=0 and not c['source_opens'] and c['source_reads']==0
for name in ('rights','rights-truncated','rights-error'):
    assert cases[name]['rights_received']==cases[name]['rights_closed']==[350,351] and cases[name]['ipc_closed']
assert cases['go-block']['code']==57 and cases['go-block']['packets_received']==[1] and [p['kind'] for p in cases['go-block']['packets_sent']]==[2]
assert cases['source-block']['code']==23 and cases['source-block']['packets_received']==[1,3]
assert cases['source-block']['packets_sent'][-1]['result']==23
assert cases['legacy-date']['code']==42 and cases['legacy-date']['packets_sent']==[]
for name in ('done-short','ipc-close'):
    assert cases[name]['source_reads']==2 and cases[name]['code']!=0 and cases[name]['packets_sent'][-1]['kind']==4
assembly=json.loads((H/'runs-final-v2/assembled/complete.json').read_text())
assert assembly['bytes']==33423360 and len(assembly['windows'])==4
assert assembly['sha256']==sha(H/'runs-final-v2/assembled/source.boot1')=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
assert not assembly['hardware_validated'] and not assembly['same_body_origin_verified']
first=json.loads((H/'runs-first/receipt/results.json').read_text());mid=json.loads((H/'runs-final/receipt/results.json').read_text())
assert first['status']=='FAIL' and first['failures']==1 and first['errors']==0
assert sha(H/'first-tested-test_ipc_gate.py')==first['source_hashes']['test_ipc_gate.py']
assert mid['status']=='PASS' and mid['tests_run']==10
for name in ('ipc_gate.inc','dynmodule.py','test_ipc_gate.py'):assert sha(H/('ten-test-passed-'+name))==mid['source_hashes'][name]
derived=json.loads((H/'source-derivation.json').read_text())
def reconstruct(original,changes):
    raw=original
    for row in changes:
        at=row['offset_in_previous'];before=row['before'].encode();after=row['after'].encode()
        assert raw.count(before)==1 and raw[at:at+len(before)]==before
        raw=raw[:at]+after+raw[at+len(before):]
    return raw
assert sha(R/derived['module_source'])==derived['module_before_sha256']
assert reconstruct((R/derived['module_source']).read_bytes(),derived['module_changes'])==(H/'boot_module.c').read_bytes()
assert sha(OLD/'handoff_impl.inc')==derived['handoff_before_sha256']
assert reconstruct((OLD/'handoff_impl.inc').read_bytes(),derived['handoff_changes'])==(H/'handoff_impl.inc').read_bytes()
assert derived['module_sha256']==D.MODULE_SHA and derived['handoff_sha256']==sha(H/'handoff_impl.inc') and derived['ipc_gate_sha256']==IPC
capture=json.loads((H/'kernel-source-capture.json').read_text());assert len(capture['files'])==5
for row in capture['files']:assert (H/row['path']).stat().st_size==row['bytes'] and sha(H/row['path'])==row['sha256']
abi=json.loads((H/'kernel-ABI-review.json').read_text());assert len(abi['checks'])==35 and abi['new_syscall_registers']==6
for row in abi['checks']:
    p=H/row['path'];assert sha(p)==row['source_sha256'];lines=p.read_text().splitlines()
    for line in row['lines']:assert lines[line['line']-1]==line['text']
layout=json.loads((H/'reference-layout-check.json').read_text())
assert layout['returncode']==0 and not layout['code_executed'] and not layout['Sony_runtime_layout_verified']
assert sha(H/'reference-layout-check.c')==layout['source_sha256']
assert layout['from_reference_header_struct'] in (H/'kernel-reference/socket-layout.h').read_text() and layout['from_reference_header_struct'] in (H/'reference-layout-check.c').read_text()
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
verification=dict(schema='fx3-stage221-private-IPC-gate-verification-v1',created_utc=now,
    status='PASS_OWN_ARM64_PRIVATE_ENTRY_GATE_GLOBAL_TARGET_KEEPER_STILL_MISSING',previous_manifest_sha256=PREV,previous_members_reverified=2387,
    module_sha256=MODULE,module_source_sha256=D.MODULE_SHA,ipc_source_sha256=IPC,tests_passed=10,entered_cases=44,own_ARM64_instances=45,
    one_guest_initialization_only=True,code_link_relocations=182,runtime_init_relocations=1,
    private_GRANT_READY_GO_DONE_checks_implemented=True,complete_wire_handoff_matches_RAM=True,
    wrong_context_inherited_descriptor_not_mutated_or_closed=True,extra_received_descriptors_closed_on_error=True,
    blocked_GO_and_source_same_guest_channel_retained_by_test_assertions=True,early_DONE_while_source_pending=False,
    safe_new_child_cmdline_bytes=13,safe_new_child_is_original_factory_argv=False,old_date_profile_rejected=True,
    own_original_shell_command_or_fork_exec_executed=False,constructor_memory_only=True,
    reference_kernel_files=5,ABI_definition_checks=35,reference_user_msghdr_native64_layout_compiled_only=True,
    actual_Linux_Sony_socket_credentials_or_parent_observed=False,live_global_keeper_integrated=False,
    privileged_parent_multiple_GRANT_global_exclusion_proven=False,stage220_controller_connected_to_protocol=False,
    trusted_launcher_or_approval_or_full_loaded_image_attested=False,real_Sony_Linux_kernel_glibc_or_loader_executed=False,
    own_ARM64_code_executed=True,formal_release04_and05_and23_sources_unchanged=True,root01_bundle_and_absent_job_unchanged=True,
    all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,goal_complete=False,persistent_write_release=False)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Own ARM64 entry now defaults deny without inherited unnamed root AF_UNIX datagram/reference-parent peer and per-message credentials, exact320B GRANT, complete256B handoff match, READY and matching GO. Extra received rights closed even on recv error; no premature DONE during source block; done/close failure nonzero. New13B shell-colon profile rejects original date string, no actual launch/auto constructor read/exit.10tests/44enteredcases/45ownARM64instances,4window33423360synthetic bytes; 5Linux4.9headers/35definitions and native msghdr layout checked. Actual global keeper/launcher/private root domain and stage220 connection missing; privileged parent can still multi-grant, no hardware/recovery/approval claim.16requirements,195pending,0.4/0.5 unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active persistent goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('221自写ARM64入口加继承私有DGRAM/参考父进程与逐消息凭据/320B GRANT→READY→GO→DONE；256B handoff与RAM全比较，无许可拒绝。新13B shell空操作合同拒绝旧日期串，无真实fork/exec/构造自动读取。错误/截断/负接收附带FD均关闭，GO/源阻塞保持原通道，DONE/close失败非0；最终10检查/44进入案例/45ARM64实例及4窗口人工源完整组装。5Linux4.9头文件/35定义和56B msghdr布局核对，6参数边界修正。真实全局keeper/启动/IPC和220连接仍缺，特权父进程多发许可仍无排他证明；16要求/195/0.4/0.5保留，无设备/root。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/boot_module.c',ipc=REL+'/ipc_gate.inc',protocol=REL+'/protocol.py',
    derivation=REL+'/source-derivation.json',builder=REL+'/dynmodule.py',tests=REL+'/runs-final-v2/receipt/results.json',build=REL+'/runs-final-v2/built/build.json',
    ABI=REL+'/kernel-ABI-review.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',module_sha256=MODULE,
    no_private_GRANT_GO_entry_denied_in_model=True,actual_global_keeper_integrated=False,new_device_operations=0)
new['latest_stage_evidence']['stage221_private_IPC_entry_gate']=ev
new['recovery_private_IPC_entry_gate']={**ev,'tests_passed':10,'entered_cases':44,'own_ARM64_instances':45,
    'new_safe_child_cmdline_bytes':13,'new_safe_child_contract_is_original_factory_argv':False,
    'reference_parent_im_actual_camera_observed':False,'actual_Linux_message_credentials_or_protected_resource_domain_verified':False,
    'privileged_parent_multiple_GRANT_global_exclusion_proven':False,'stage220_live_owner_connected_to_binary_protocol':False,
    'same_body_backup_restore_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01具体问题待答；不从active/继续推导批准，不启动或重问，不扩大相机权限。',
    '221新候选已拒绝无私有GRANT/GO入口，但全局监管端缺失，合格特权父进程仍能同时发多个许可。下一项实现与320B协议对应的Linux ARM64父端共享占用/串行状态、逐消息凭据、实际子进程退出及异常保持UNKNOWN；先双端假内核验证，不能把预置GO或Mac220的独立测试当端到端排他。',
    '当前父进程仍按im参考文件过滤，新13B shell空操作为新合同，未实际fork/exec/显式分派。若用独立keeper必须同步修订父身份合同；若在父im扩展中运行则核实加载/创建通道/明确退出路径，避免旧日期副作用和原无界wait。真实root固定域/完整代码/用户批准不能由凭据/nonce/SHA推断。',
    '保留全部16要求、同机健康boot/p1/完整配置、真实数据视图和访问归还、独立AP入口、逆写/冷启动及MAIN1080p29.97 HEVC/长录。新私有门和合成组装不充真实备份/救砖/首刷放行。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=encode(new);index=R/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3自写ARM64私有许可入口](<'+REL+'/README.md>)：无GRANT/GO默认拒绝，256B handoff全绑定；10检查/44进入案例、5Linux头文件/35定义及布局核对通过，四窗口人工源完整组装。新13B空操作合同拒绝旧日期串；机内全局keeper/启动/真实凭据仍缺，16要求/195/0.5不变，无设备/root。'
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
put('final-receipt.json',dict(schema='fx3-stage221-private-IPC-entry-gate-v1',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=2387,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
    tests_passed=10,entered_cases=44,own_ARM64_instances=45,module_sha256=MODULE,
    no_private_GRANT_GO_entry_denied_in_model=True,actual_global_keeper_integrated=False,
    privileged_parent_multiple_GRANT_global_exclusion_proven=False,new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=10,entered_cases=44,
    own_ARM64_instances=45,module_sha256=MODULE,actual_global_keeper_integrated=False,requirements_unchanged=16,
    new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
