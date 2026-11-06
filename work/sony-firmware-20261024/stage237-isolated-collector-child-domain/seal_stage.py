"""Seal a conditional private collector core, not a complete target probe."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,importlib.util,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage236-kernel-unique-exit-interface-audit';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def load(p):return json.loads(p.read_text())
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='7af58f2d8b0cf256eda267663768d84b5217fe0c4732836b5d9fd9a36dd0b0f0'
pm=load(P/'final-receipt.json');assert len(pm['files'])==34
for row in pm['files']:
 p=R/row['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
t=load(H/'runs-private-domain/receipt.json');assert t['status']=='SCOPED_CHECKS_PASS_WITH_REQUIRED_CLOSED_DOMAIN_BOUNDARY' and t['tests']==8 and len(t['cases'])==22 and t['failures']==t['errors']==0
for n,digest in t['source_hashes'].items():assert sha(H/n)==digest
cases={r['fault']:r for r in t['cases']};assert len(cases)==22
for row in cases.values():assert not row['source_accesses'] and row['host_borrowed_FDs_unchanged'] and row['only_collector_created_child']
for f in [None,'between-recv-wait']:assert cases[f]['collector_exit_status']==2560 and cases[f]['collector_state']==10 and cases[f]['own_worker_status']==0 and cases[f]['worker_reaped']
for f in ['multi-thread','tid-mismatch','subreaper','traced','unblocked','existing-child','status-open','prctl-unavailable']:assert cases[f]['collector_exit_status']==1024 and cases[f]['own_worker_status'] is None and not any(x['event']=='clone0' for x in cases[f]['events'])
for f,n in [('worker-close-error',17408),('SIGKILL-after-DONE',9)]:assert cases[f]['collector_exit_status']==512 and cases[f]['own_worker_status']==n
assert cases['stall']['collector_alive'] and cases['stall']['own_worker_alive'] and cases['stall']['collector_state']==2 and cases['stall']['collector_exit_status'] is None
assert cases['late-zero']['own_worker_status']==0 and cases['late-zero']['collector_exit_status']==512
for f in ['external-reap-cousin','external-reap-host-child']:assert cases[f]['own_worker_status']==17408 and cases[f]['collector_alive'] and cases[f]['collector_state']==2 and all('foreign replacement' not in w['eligible_roles'] for w in cases[f]['waits'])
bad=cases['illegal-parent-injection'];assert bad['own_worker_status']==17408 and bad['collector_exit_status']==2560 and any(x.get('closed_tree_contract_violated') for x in bad['events']) and t['illegal_same_parent_injection_still_false_completes'] and t['closed_child_domain_is_required_not_optional'] and not t['probe_deployable'] and not t['first_flash_released']
assert cases['collector-killed']['collector_exit_status']==9 and cases['collector-killed']['collector_state']!=10
assert not t['outer_bootstrap_parent_exit_binding_and_host_completion_implemented'] and t['only_own_ARM64_executed'] and not t['actual_Linux_processes_or_threads_created'] and not t['original_Sony_Linux_glibc_or_driver_executed'] and t['new_device_operations']==0
repro=load(H/'reproducible-build-summary.json');assert repro['status']=='PASS' and repro['source_hashes']==t['source_hashes'] and not repro['deployable']
binary=H/'build-current/collector.elf';assert sha(binary)==sha(H/'reproducible-build/collector.elf')==repro['binary_sha256']==t['binary_sha256']=='d87dce5b1fdfcac38c99081464d5751ffe609e9331d20a0bf10de5de1ce65eb1' and binary.stat().st_size==262144
spec=importlib.util.spec_from_file_location('isolated237_seal',H/'isolated_build.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);segments=D.read_executable(binary.read_bytes());assert len(segments)==4 and all(not(s['flags']&1 and s['flags']&2) for s in segments)
for folder in ['build-current','reproducible-build']:
 q=load(H/folder/'build.json');assert q['source_sha256']==sha(H/'collector.c') and q['return10_means_inner_worker_exit_observed_only'] and not q['outer_bootstrap_implemented'] and not q['deployable']
 assert (H/'collector.c').read_bytes()==(H/folder/'collector.c').read_bytes() and (H/folder/'entry.s').read_bytes()==D.ENTRY_SOURCE and (H/folder/'compiler.stderr.txt').read_bytes()==b''
revision=load(H/'source-revisions.json');assert revision['final_source_sha256']==sha(H/'collector.c') and revision['initial_failed_source_sha256']==sha(H/'build-first/collector.c') and revision['final_source_equals_both_successful_build_snapshots'] and b'misleading indentation' in (H/'build-first/compiler.stderr.txt').read_bytes()
origin=load(H/'builder-origin.json');assert sha(R/origin['path'])==origin['sha256']
a=load(H/'private-domain-contract.json');assert a['status']=='SAVED_NATIVE_AND_REFERENCE_CONTRACT_PASS_NOT_RUNTIME_ACCEPTANCE' and a['checks']==len(a['check_names'])==53 and len(a['source_ranges'])==10
assert sha(R/a['original_kernel'])==a['original_kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c' and not a['real_entry_creation_and_signal_mask_precondition_proven'] and not a['collector_exit_binding_to_outer_service_parent_proven']
raw=(R/a['original_kernel']).read_bytes();spans=load(H/'original-process-domain-spans.json');assert len(spans)==3
for row in spans:
 p=raw[row['start']:row['end']];assert len(p)==row['bytes']==4*len(row['instructions']) and sha256(p).hexdigest()==row['sha256']
 for i,x in enumerate(row['instructions']):assert x['offset']==row['start']+i*4 and bytes.fromhex(x['word'])==p[i*4:i*4+4]
for row in a['source_ranges']:
 p=R/row['path'];piece=''.join(p.read_text().splitlines(keepends=True)[row['first_line']-1:row['last_line']]);assert sha(p)==row['sha256'] and sha256(piece.encode()).hexdigest()==row['range_sha256'] and all(s in piece for s in row['required_tokens'])
captures=load(H/'source-capture.json');assert len(captures)==4
for row in captures:assert row['status']=='CAPTURED' and sha(H/row['path'])==row['sha256'] and (H/row['path']).stat().st_size==row['bytes']
law=load(H/'topology-law-receipt.json');assert law['source_sha256']==sha(H/'topology_law_model.py') and len(law['cases'])==14 and all(not x['matches_collector_child_domain'] for x in law['cases']) and law['code_integrity_boundary']['closed_domain_broken'] and law['real_outer_bootstrap_unverified'] and law['not_a_proof_of_actual_target_process_tree']
old=load(B/'stage235-single-load-preparation-and-exit-observer/remaining-parent-identity-counterexample.json');assert old['current_false_complete'] and old['must_not_release_this_candidate'] and old['original_own_child_exit']==68 and old['result']==[3,0]
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for row in release['files']:assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();prior=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(prior['requirements'])==16 and not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='CONDITIONAL_PRIVATE_COLLECTOR_CORE_PASS_GLOBAL_ADMISSION_NOT_PASSED',scoped_checks=8,own_ARM64_model_cases=22,static_native_checks=53,native_spans=3,source_ranges=10,source_graph_cases=14,own_ELF_sha256=sha(binary),own_ELF_bytes=binary.stat().st_size,private_collector_core_implemented=True,inner_worker_exit_observation_only=True,foreign_same_parent_boundary_counterexample_retained=True,closed_child_domain_code_integrity_and_real_entry_proven=False,outer_collector_exit_and_host_completion_proven=False,full_boot_worker_integrated=False,probe_deployable=False,stage235_candidate_unchanged_and_admission_still_failed=True,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:236 actual saved-kernel wait identity interfaces and remaining finite counterexamples sealed',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=34,test_receipt='runs-private-domain/receipt.json',kernel_contract='private-domain-contract.json',law='topology-law-receipt.json',reproducible_build='reproducible-build-summary.json',conditional_tests_do_not_override_unverified_entry_or_boundary_counterexample=True,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Own isolated collector core and NOOP worker cross compiled to262144B import-free static ARM64 ELF with identical rebuild.8checks22cases include process guard rejection, exact worker0 versus exit68/SIGKILL, recv/wait race, private message/FD failure, sticky timeout/late0, external reap+foreignPID with source-derived valid parent, and collector death.53native checks3spans10source ranges pin private clone children/signal state, parent selection, actual PR_GET_CHILD_SUBREAPER table and bit.14finite parent graphs separate valid external parent from arbitrary assignment. Explicit illegal same-parent boundary still wrongly accepts old68 asforeign0 if closed-domain contract broken; no real bootstrap, private creation/mask/image/request binding or outer collector exit proof, so global admission remains unpassed.235original unchanged+failed. No source/device/admin operation;16requirements and formal0.4/0.5/195 preserved.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('237实现隔离监管核心/空操作，262144B自写ARM64重复构建；8检查22场景在显式内核中验证单线程/无收养/空子域前置、真实exit68或SIGKILL不充DONE成功、超时晚0保持、外部合法父关系PID替换拒绝。53原字检查3范围10源码段及14父关系图固定实际克隆/PR_GET分支。强行同父注入仍误认，代码完整性/真实隔离入口与监管者自身退出未闭合，局部10不充整体完成；235原候选未改且准入仍失败。16/195/正式包保留，无设备/root。')
ev=dict(readme=rel+'/README.md',source=rel+'/collector.c',builder=rel+'/isolated_build.py',model=rel+'/model_collector.py',test_receipt=rel+'/runs-private-domain/receipt.json',kernel_contract=rel+'/private-domain-contract.json',source_graph=rel+'/topology-law-receipt.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage237_isolated_collector_child_domain']=ev;new['recovery_isolated_collector_child_domain']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['把237隔离核心接入真实前置的clone0/创建前信号屏蔽、匿名代码存活、实际父PID和完整计划SHA/任务关联；现固定321与消息关联是人工值，快照不充后续代码完整性，不能投放。','单独解决监管者自身退出/外层回收与主机完成凭据，不将内部工作器局部10充整体完成；Sony服务线程不得直接调用可能长期HELD的核心。保留235当前失效准入及同父边界反例。','证明固定工作器不再fork/clone/exec及接收边界；若工作器额外生成CLONE_PARENT兄弟会破坏封闭域。53原字/14图/22场景是条件证据，实际目标进程、入口及请求时限未验。','入口闭合后整合完整boot采集/主机回传、同机健康备份、独立AP救砖逆写冷启动及MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录全部16要求；195root01未批准不启动，正式0.4/0.5及23源码不变。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert prior[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3隔离监管与封闭子进程域核心](<'+rel+'/README.md>)：自写ARM64核心8检查22场景/重复构建，53原字核对与14父图；限定域拒绝外部PID复用，保留强行同父反例。真实隔离入口/监管者退出/完整采集未闭合，235准入仍失败；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage237-conditional-private-collector-core-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
