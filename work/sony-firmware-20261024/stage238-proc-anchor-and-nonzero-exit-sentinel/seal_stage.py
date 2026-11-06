"""Seal an object-relative/sentinel observer; do not certify whole-job exit."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,importlib.util,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage237-isolated-collector-child-domain';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='88c2a667680c3a9ef7b7c3a001dfb7e841fb04a3215ac9d9c7bb88fe6a4c6101'
pm=load(P/'final-receipt.json');assert len(pm['files'])==50
for x in pm['files']:
 p=R/x['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
t=load(H/'runs-object-observer-final/receipt.json');assert t['status']=='SCOPED_OBJECT_OBSERVER_PASS_WITH_ANCHOR_ORIGIN_BOUNDARY' and t['tests']==9 and len(t['cases'])==39 and t['failures']==t['errors']==0
for n,d in t['source_hashes'].items():assert sha(H/n)==sha(H/'runs-object-observer-final/source-snapshot'/n)==d
cases={x['name']:x['summary'] for x in t['cases']};assert len(cases)==39
for x in cases.values():assert not x['waits'] and x['no_numeric_pid_path_lookup_or_wait'] and x['new_stat_FDs_all_closed'] and x['host_borrowed_FDs_unchanged']
pair=cases['same-live-object-pair'];assert pair['result']==11 and pair['producer']['collector_exit_status']==10752 and pair['producer']['own_worker_status']==0 and pair['same_live_process_object_used_by_both_own_machines'] and len(pair['self_proc_anchor_transfers'])==1
assert all(x['object']=='same running collector object A' for x in pair['lookups'])
for f in ['worker-close-error','SIGKILL-after-DONE','wrong-DONE','collector-killed']:assert cases['paired-'+f]['result']==2 and cases['paired-'+f]['producer']['collector_exit_status']!=10752
filtered=cases['paired-filtered-sentinel'];assert filtered['result']==2 and filtered['producer']['collector_exit_status']==10752
assert cases['reuse-after-evidence']['result']==11 and all(x['object']=='original object A' for x in cases['reuse-after-evidence']['lookups'])
for n in ['numeric-reuse-before-evidence','gone-before-evidence','live-zero','zombie-only']:assert cases[n]['result']==2
bad=cases['untrusted-origin-boundary-counterexample'];assert bad['result']==11 and bad['collector_kernel_raw_status']==9 and bad['anchor_origin']=='foreign object B'
bad=cases['private-child-domain-boundary-counterexample'];assert bad['result']==11 and bad['producer']['own_worker_status']==17408 and bad['producer']['collector_exit_status']==10752
assert t['self_proc_anchor_sender_implemented'] and not t['parent_native_SCM_receiver_and_authentic_creation_bridge_implemented'] and t['arbitrary_wrong_origin_anchor_can_still_false_complete'] and not t['deployable'] and t['new_device_operations']==0 and not t['original_Sony_Linux_or_glibc_executed'] and not t['actual_Linux_processes_or_threads_created']
spec=importlib.util.spec_from_file_location('candidate238_seal',H/'candidate_build.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
repro=load(H/'reproducible-build-summary.json');assert repro['status']=='PASS' and repro['source_hashes']==t['source_hashes'] and not repro['deployable']
pins={'collector':('build-collector-anchor','3484301d208b649f60fd53ab79e6d7600f878bcb8ba58ddab675bec4b40d4f27','collector-anchor.c'),'observer':('build-observer','924e0508a74c31a0ee0c6eb6d5647eb354ceb954a749ec74e77e2314e5a8d863','observer.c')}
for role,(folder,digest,source) in pins.items():
 p=H/folder/(role+'.elf');assert sha(p)==sha(H/('repro-'+role)/(role+'.elf'))==digest==t[role+'_sha256']==repro[role+'_sha256'] and p.stat().st_size==262144
 seg=D.read_executable(p.read_bytes());assert len(seg)==4 and all(not(x['flags']&1 and x['flags']&2) for x in seg)
 for f in [folder,'repro-'+role]:
  x=load(H/f/'build.json');assert sha(H/f/'source.c')==sha(H/source)==x['source_sha256'] and sha(H/f/'entry.s')==x['entry_source_sha256'] and not x['deployable'] and (H/f/'compiler.stderr.txt').read_bytes()==b''
a=load(H/'proc-anchor-contract.json');assert a['checks']==len(a['check_names'])==58 and len(a['source_ranges'])==12 and a['nonzero_sentinel']==10752 and a['raw_filtered_exit_status_zero_can_look_like_normal0'] and a['native_EXIT_ZOMBIE_value']==32 and a['native_EXIT_DEAD_value']==16
assert not a['complete_native_all_path_exit_files_dominance_proven'] and not a['proc_PID_detachment_is_all_kernel_post_exit_cleanup_complete'] and not a['native_parent_SCM_receiver_and_authentic_entry_binding_proven'] and not a['original_code_executed']
raw=(R/a['original_kernel']).read_bytes();assert sha256(raw).hexdigest()==a['original_kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c';spans=load(H/'original-proc-object-spans.json');assert len(spans)==7
for x in spans:
 p=raw[x['start']:x['end']];assert len(p)==x['bytes']==4*len(x['instructions']) and sha256(p).hexdigest()==x['sha256']
 for i,j in enumerate(x['instructions']):assert j['offset']==x['start']+i*4 and bytes.fromhex(j['word'])==p[i*4:i*4+4]
for x in a['source_ranges']:
 p=R/x['path'];piece=''.join(p.read_text().splitlines(keepends=True)[x['first_line']-1:x['last_line']]);assert sha(p)==x['sha256'] and sha256(piece.encode()).hexdigest()==x['range_sha256'] and all(t in piece for t in x['required_tokens'])
capture=load(H/'source-capture.json')+[load(H/'self-source-capture.json')];assert len(capture)==4
for x in capture:assert x['status']=='CAPTURED' and (H/x['path']).stat().st_size==x['bytes'] and sha(H/x['path'])==x['sha256']
zero=load(H/'zero-filter-counterexample.json');assert zero['kernel_contract_sha256']==sha(H/'proc-anchor-contract.json') and len(zero['cases'])==2 and all(x['naive_accept_zero'] and not x['correct_fixed_nonzero_observer_accepts'] for x in zero['cases'])
rev=load(H/'source-revisions.json');assert rev['final_collector_source_sha256']==sha(H/'collector-anchor.c') and rev['initial_collector_sha256']==sha(H/'build-collector/collector.elf')
old=load(H/'runs-object-observer/receipt.json');assert old['errors']==2
for n,d in old['source_hashes'].items():assert sha(H/'runs-object-observer/source-snapshot'/n)==d
old=load(H/'runs-object-observer-v2/receipt.json');assert old['tests']==8 and len(old['cases'])==37 and old['errors']==old['failures']==0
for n,d in old['source_hashes'].items():assert sha(H/'runs-object-observer-v2/source-snapshot'/n)==d
for filename in ['builder-origin.json','collector-source-origin.json']:
 x=load(H/filename);assert sha(R/x['path'])==x['sha256']
old=load(B/'stage235-single-load-preparation-and-exit-observer/remaining-parent-identity-counterexample.json');assert old['must_not_release_this_candidate'] and old['current_false_complete']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();prior=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(prior['requirements'])==16 and not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='CONDITIONAL_PROC_OBJECT_EXIT_AND_DETACH_PASS_GLOBAL_ADMISSION_NOT_PASSED',own_checks=9,own_model_cases=39,native_static_checks=58,native_spans=7,source_ranges=12,each_own_ELF_bytes=262144,collector_sha256=t['collector_sha256'],observer_sha256=t['observer_sha256'],self_proc_anchor_sender_implemented=True,same_live_model_process_object_pair_executed=True,zero_filtered_exit_status_false_success_rejected=True,native_parent_receiver_and_authentic_entry_binding_proven=False,two_boundary_counterexamples_retained=True,all_kernel_post_exit_cleanup_or_full_job_and_USB_completion_proven=False,probe_deployable=False,stage235_candidate_unchanged_and_admission_still_failed=True,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:237 private collector core conditional tests and source domain contract sealed',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=50,test_receipt='runs-object-observer-final/receipt.json',native_contract='proc-anchor-contract.json',zero_counterexample='zero-filter-counterexample.json',all_scope_limits_preserved=True,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Own collector self-opens proc directory and sendsSCM_RIGHTS anchor, fixed _start maps only inner10 to normalexit42; observer reads original object relative stat and requires exact10752/Z then task detach, no numericPIDwait. Same live fake process shared by two own ARM64 machines;9checks39cases/reproducible two262144B ELFs.58saved native checks7spans12source ranges bind inodePIDrefs and actual ptrace-denial zero filter. Naive zero false-success rejected; proc PID detachment is not all kernel post-exit cleanup or full job/USBreturn. Wrong-origin samePID/start FD and broken inner closed-domain still false complete in explicit boundary cases; parent native receiver, authenticated creation/mask/anonymous-image/plan linkage not implemented, global admissionunpassed.235unchangedfailed; no device/root,16requirements/formal0.4/0.5/195unchanged.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('238自写监管者主动SCM_RIGHTS发送自身proc目录，固定_start将内部10映成exit42；原对象观察器核对Z/10752后task脱离，同活模型对象双端自写ARM649检查39场景、两262144B重复构建通过。58原字检查7范围12源码段证实权限可把exit_code滤成0，固定非零避免此误报。来源错误及内层封闭域破坏两反例保留，父端原生接收/真实创建/计划绑定未闭合；不充全部内核清理/全任务/USB归还。16/195/正式包不变，无设备/root，准入未通过。')
ev=dict(readme=rel+'/README.md',collector=rel+'/collector-anchor.c',observer=rel+'/observer.c',builder=rel+'/candidate_build.py',model=rel+'/model_observer.py',tests=rel+'/runs-object-observer-final/receipt.json',native_contract=rel+'/proc-anchor-contract.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage238_proc_anchor_nonzero_exit_sentinel']=ev;new['recovery_proc_anchor_nonzero_exit_sentinel']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['实现父端C的SCM_RIGHTS接收/精确凭据/唯一目录FD验证与失败权利清理，证明anchor来自本次真实clone子进程而非同PID/同起时外国对象；238仅发送端已实现，固定321/53/777与关联仍为夹具，不能投放。','把独立clone前的信号屏蔽、匿名代码持续存活、父请求/完整计划SHA和来源验证接到237核心与238对象观察器；封闭子域被破坏仍可能误将原worker68变成collector42，不能以新增观察器清除该前提。','严格区分原对象Z/10752+task脱离与全部内核退出后清理/源FD/整任务/USB归还；普通exit0可能是权限滤零，不充成功。当前235准入仍失败，39范围内场景和58原字检查不充实机验收。','入口合同闭合后整合完整boot采集及主机回传、同机健康备份与独立AP救砖逆写冷启动、MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16项；195root01未批准不启动，正式0.4/0.5及23源码保留。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert prior[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3原对象句柄与非零退出标记](<'+rel+'/README.md>)：自传proc目录FD/exit42与原对象观察器，9检查39场景及双端重复构建；58原字核对固定权限滤零陷阱。父端接收/真实入口与两来源/子域反例仍未闭合，不充全任务或USB归还；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage238-conditional-proc-object-nonzero-exit-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
