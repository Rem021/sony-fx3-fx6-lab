"""Verify and register own request/claim candidate; no device or root calls."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
import ast, json, os, plistlib, re, stat, subprocess, sys

H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
T=R/'outputs/fx3-recovery-adapter';P=B/'stage218-fixed-shell-process-filter'
REL=str(H.relative_to(R))
PREVIOUS='470396cf0542fbf3395777fcfd21df00b8d78e2b31a2d691f1518600e52caff5'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
MODULE='be0805584b07e116d26da2ee8036a67cbd9c65801efdaedab47e995f33e3030d'
HAND='5788e13bcd0335ac3928433d8cb54d6b3e1eb0a587cc9845ae9dbee3f3d04fee'
INNER='a1459db35501716dc414b45479aaa25c1ddb252ec440bd24258c4db7dbd78683'

def sha(p):return sha256(p.read_bytes()).hexdigest()
def encode(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(name,value):(H/name).open('xb').write(encode(value))
def volume():
    info=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert info['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

volume();assert not (H/'final-receipt.json').exists()
assert sha(P/'final-receipt.json')==PREVIOUS
previous=json.loads((P/'final-receipt.json').read_text());assert len(previous['files'])==106
for row in previous['files']:
    p=R/row['path'];s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size==row['bytes'] and sha(p)==row['sha256']

sys.path.insert(0,str(H));import dynmodule as D;import handoff as W
r=json.loads((H/'runs-final-v2/receipt/results.json').read_text());build=r['build']
assert r['status']=='PASS_OWN_HANDOFF_AND_REQUEST_CLAIM_FIXTURES' and r['tests_run']==11 and r['failures']==r['errors']==0
assert len(r['cases'])==len(r['guests'])==50
assert sha(H/'test_handoff.py')==r['test_source_sha256']
assert sha(H/'dynmodule.py')==r['builder_source_sha256']
assert sha(H/'handoff.py')==r['handoff_python_source_sha256']
assert sha(H/'boot_module.c')==D.MODULE_SHA==build['module_source_sha256']
assert sha(H/'handoff_impl.inc')==build['handoff_implementation_sha256']==HAND
assert sha(H/'inner_boot_reader.c')==build['inner_reader_sha256']==INNER
assert build['sha256']==MODULE and build['bytes']==262936
assert len(build['link_relocations'])==166 and len(build['runtime_relocations'])==1
assert sha(H/'runs-final-v2/built/boot-module.so')==sha(H/'runs-final-v2/reproducible/boot-module.so')==MODULE
fmt=D.inspect((H/'runs-final-v2/built/boot-module.so').read_bytes())
assert set(fmt['exports'])=={'fx3_boot_read_window','fx3_module_status'}
assert not fmt['actual_Sony_loader_acceptance_verified'] and not fmt['initialization_behavior_verified_by_inspector']
assert build['request_binding_and_pending_claims_implemented'] and not build['cross_request_global_exclusion_implemented']
assert not build['source_initializer_calls_worker_or_syscall'] and not build['exclusive_request_attestation_verified']
assert r['actual_host_O_EXCL_on_regular_files'] and r['own_ARM64_code_executed']
assert not r['Sony_or_Linux_kernel_or_glibc_executed'] and not r['real_root_UID_isolation_or_camera_tmpfs_verified']
assert r['camera_operations']==0 and not r['flashable'] and not r['independent_recovery_proven']
assert all(not g['errors'] and g['calls'][0]['syscalls']==0 for g in r['guests'])
assert all(c['number'] not in (35,93,94) for g in r['guests'] for c in g['syscalls'])
cases={c['name']:c for c in r['cases']};assert len(cases)==50
assert [cases['full-'+str(i)]['source_reads'] for i in range(4)]==[128,128,128,126]
assert all(cases['full-'+str(i)]['code']==0 for i in range(4))
for name in ['replay-next','nonce-next','request-changes','after-claim-expiry']:
    assert cases[name]['code']!=0 and cases[name]['source_opens']==[] and cases[name]['source_reads']==0
assert cases['field-32']['code']==cases['field-64']['code']==0  # association, not secret authorization
assert cases['late-completion']['code']==50 and cases['late-completion']['source_reads']==2

held=[]
for fault in ('claim-short-write','claim-sync','claim-close'):
    assert cases[fault]['code']==52 and cases[fault]['source_opens']==[]
    for suffix in ('-replay','-fresh-nonce'):
        assert cases[fault+suffix]['code']==51 and cases[fault+suffix]['source_opens']==[]
    folder=H/'runs-final-v2'/(fault+'-shared');paths=sorted(folder.glob('*.pending'))
    assert len(paths)==3
    assert (folder/('capture-'+'b'*32+'-b0-w0.pending')).exists()
    for p in paths:
        raw=p.read_bytes()
        try:
            decoded=W.decode_claim(raw);assert not decoded['receipt_authenticated'] and not decoded['operation_complete']
            valid=True
        except ValueError:valid=False
        held.append(dict(path=str(p.relative_to(H)),bytes=len(raw),valid_record=valid,
                         name_remains_held=True,is_completion=False))
children=r['real_host_process_results'];assert len(children)==2
assert sorted(x['guest_result'] for x in children)==[0,51] and sum(x['source_reads'] for x in children)==2
assert len({x['os_pid'] for x in children})==2
assert all(x['module_sha256']==MODULE and x['modeled_PID_equals_actual_test_PID']
           and not x['actual_target_root_or_Linux_process_verified'] and not x['Sony_or_Linux_code_executed'] for x in children)
assembled=json.loads((H/'runs-final-v2/assembled/complete.json').read_text())
assert assembled['bytes']==33423360 and len(assembled['windows'])==4
assert sha(H/'runs-final-v2/assembled/source.boot1')==sha(H/'runs-final-v2/fixture/synthetic.boot')==assembled['sha256']=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
assert not assembled['hardware_validated'] and not assembled['same_body_origin_verified'] and not assembled['atomic_snapshot_proven']
assert len(list((H/'runs-final-v2/full-shared').glob('*.pending')))==8

gap=json.loads((H/'live-gap-current-v2/receipt/gap.json').read_text())
assert gap['status']=='CONFIRMED_OPEN_CROSS_REQUEST_EXCLUSION_GAP_IN_FAKE_KERNEL_MODEL'
assert gap['module_sha256']==sha(H/'live-gap-current-v2/built/boot-module.so')==MODULE
assert gap['handoff_implementation_sha256']==HAND and gap['module_source_sha256']==D.MODULE_SHA
assert gap['reproduction_source_sha256']==sha(H/'reproduce_cross_request_gap.py')
assert gap['evidence']==dict(first_still_live=True,first_has_not_returned=True,first_source_reads=1,second_result=0,second_source_reads=2)
assert gap['first_return_after_cooperative_release']==23
assert not gap['readiness_pass'] and not gap['camera_deployment_released'] and gap['new_camera_operations']==0

derived=json.loads((H/'inner-derivation.json').read_text());raw=(R/derived['source']).read_bytes()
assert sha256(raw).hexdigest()==derived['source_sha256']==D.B.SOURCE_SHA
assert len(derived['ordered_changes'])==4 and derived['all_other_bytes_preserved']
for row in derived['ordered_changes']:
    at=row['offset_in_previous'];before=row['before'].encode();after=row['after'].encode()
    assert raw.count(before)==1 and raw[at:at+len(before)]==before
    raw=raw[:at]+after+raw[at+len(before):]
assert raw==(H/'inner_boot_reader.c').read_bytes() and sha256(raw).hexdigest()==derived['derived_sha256']==INNER
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text())
assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link not in ('verification-receipt.json','final-receipt.json'):
        assert (H/link.strip('<>')).resolve().exists(),link

canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-final.json').read_text())
assert old['latest_stage']==P.name and len(old['requirements'])==16
assert native['goal']['status']=='active' and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
verification=dict(schema='fx3-stage219-bound-handoff-request-claims-verification-v1',created_utc=now,
    status='PASS_REQUEST_AND_WINDOW_FENCES_WITH_CONFIRMED_OPEN_GLOBAL_EXCLUSION_GAP',
    previous_manifest_sha256=PREVIOUS,previous_members_reverified=106,
    module_sha256=MODULE,module_source_sha256=D.MODULE_SHA,handoff_source_sha256=HAND,inner_reader_sha256=INNER,
    tests_passed=11,own_ARM64_cases=50,real_ordinary_Mac_processes=children,
    synthesized_boot_bytes=assembled['bytes'],synthesized_boot_sha256=assembled['sha256'],window_chunks=[128,128,128,126],
    both_claim_names_reserved_before_write=True,partial_claims=held,claim_is_trusted_completion=False,
    cross_request_global_exclusion_implemented=False,live_cross_request_overlap_reproduced=gap,
    own_ARM64_code_executed=True,Sony_Linux_glibc_loader_or_camera_execution=False,
    actual_root_isolation_or_camera_tmpfs_verified=False,target_clock_or_PID_live_observed=False,
    trusted_launcher_or_complete_receipt_verified=False,inner_source_derived_by_four_documented_changes=True,
    formal_release04_and05_and23_sources_unchanged=True,root01_bundle_and_absent_job_unchanged=True,
    all16_requirements_and_authorizations_unchanged=True,new_camera_USB_or_root_operations=0,
    goal_complete=False,persistent_write_release=False)
new=deepcopy(old)
new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Added256byte handoff binding full128byte boot request/PID/PPID/range/nonce/operator plan digest/target-clock expiry. Private0.5 reader derived by4changes rechecks bound request/deadline. Two immutable tmpfs claim names reserved before writes; zero/partial/sync/close failures retain same-window fence with fresh nonce.11tests/50ownARM64cases plus2ordinaryMacprocesses pass;4windows reconstruct33423360synthetic bytes. Final module live negative reproduction confirms distinct captureIDs can overlap while first read blocks: global exclusion OPEN, not readiness. No Sony/Linux/root/device execution; authority/completion/clock/camera origin unproven.16requirements,195pending,0.4/0.5 unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-final.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['current_manual_goal_continuation']=dict(user_request='Continue active persistent goal',receipt=REL+'/native-goal-observed.json',classification='progress',native_status_remains='active',same_blocker_no_progress_count=0,meaningful_safe_offline_work_remains=True,assistant_resumed_native_goal=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification']
new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('219接入256B handoff与完整请求/PID/父PID/范围/nonce/期限关联；两个占用名先独占创建再写，短写/同步/关闭失败后新nonce不能绕过同窗口。4处内层源码派生保持其余字节，11最终测试/50自建ARM64案例+2普通Mac子进程，4窗口合成33,423,360B完整组装。最终二进制并发反例确认不同采集任务仍可重叠，明确OPEN非放行；可信启动者/完成与同机视图/归还/独立恢复未验。16要求/195待答/0.4/0.5不变，无设备/root。')
evidence=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',source=REL+'/boot_module.c',handoff=REL+'/handoff_impl.inc',producer=REL+'/handoff.py',
    derivation=REL+'/inner-derivation.json',builder=REL+'/dynmodule.py',tests=REL+'/runs-final-v2/receipt/results.json',build=REL+'/runs-final-v2/built/build.json',
    module_sha256=MODULE,scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',global_gap=REL+'/live-gap-current-v2/receipt/gap.json',
    own_ARM64_code_executed=True,Sony_or_Linux_execution=False,new_device_operations=0)
new['latest_stage_evidence']['stage219_bound_handoff_request_claims']=evidence
new['recovery_bound_handoff_and_request_claims']={**evidence,'tests_passed':11,'own_ARM64_cases':50,'ordinary_Mac_subprocesses':2,
    'same_nonce_and_capture_window_fenced_in_model':True,'both_claim_names_reserved_before_writes':True,
    'global_cross_request_exclusion':False,'live_global_exclusion_gap_reproduced':True,
    'claim_is_completion':False,'target_PID_clock_or_origin_observed':False,
    'trusted_launcher_or_completion_ready':False,'Sony_loader_backup_restore_or_flash_readiness_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01具体问题待答；不从active/继续推导批准，不启动或重问，不扩大相机权限。',
    '219已接入请求与同nonce/同采集窗口跨进程防重复，但最终构建并发反例确认不同captureID仍可同时读。下一项接共享全局在途占用：阻塞/超时/死亡保留UNKNOWN，不凭PID消失或可写JSON释放；保留正常4窗口采集能力，先不访问真实源的离线验证。',
    '计划摘要/nonce/CRC/SHA/PID与调用方提供目标时钟只作关联；仍需可信启动者、真实父im/子BusyBox与完成通道。不能将进程匹配直接当授权，不触发旧日期命令、上传模块或安装preload。',
    '真实Sony装载/受控退出未验，原日期副作用、fork失败退出调用者及无超时wait仍在；保持全部16要求、同机健康boot/p1/完整配置、数据视图/归还、独立AP入口、逆写/冷启动及MAIN1080p29.97 HEVC/长录验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[key]==old[key],key
for key in old['latest_stage_evidence']:assert new['latest_stage_evidence'][key]==old['latest_stage_evidence'][key]
assert not new['goal_complete'] and not new['persistent_write_release']
after=encode(new);index=R/'README.md';index_before=index.read_bytes()
marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3请求绑定与窗口防重复候选](<'+REL+'/README.md>)：11项/50自建ARM64案例及2普通Mac进程通过，4窗口组装33,423,360B合成数据；两占用名先留位，部分失败后换nonce仍拒绝。最终并发反例确认不同任务可重叠，全局排他/可信完成仍缺；16要求/195待答/0.5保留，无设备/root。'
text=index_before.decode();assert text.count(marker)==1 and entry not in text
index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'concurrent head change'
put('verification-receipt.json',verification)
(H/'goal-status-after.json').open('xb').write(after)
(H/'readme-rebased-before.md').open('xb').write(index_before)
(H/'readme-after.md').open('xb').write(index_after)
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,index_after,'.index.tmp',index_before)]:
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
put('final-receipt.json',dict(schema='fx3-stage219-bound-handoff-request-claims-v1',created_utc=now,
    previous_manifest_sha256=PREVIOUS,previous_members_reverified=106,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
    tests_passed=11,own_ARM64_cases=50,ordinary_Mac_subprocesses=2,module_sha256=MODULE,
    global_cross_request_gap_confirmed_open=True,trusted_launcher_or_completion_proven=False,
    new_camera_USB_or_root_operations=0,root01_bundle_sha256_unchanged=HOST,new_approval_granted=False,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=sha(H/'final-receipt.json'),members=len(members),tests_passed=11,
    own_ARM64_cases=50,ordinary_Mac_subprocesses=2,module_sha256=MODULE,global_gap_remains_open=True,
    requirements_unchanged=16,native_goal_status='active',new_camera_operations=0,goal_complete=False,persistent_write_release=False)))
