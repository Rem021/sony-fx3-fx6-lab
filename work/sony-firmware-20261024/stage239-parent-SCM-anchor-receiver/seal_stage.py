"""Seal own C receive/ACK progress; origin and true entry remain unproven."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,importlib.util,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage238-proc-anchor-and-nonzero-exit-sentinel';T=R/'outputs/fx3-recovery-adapter'
def sha(p):return sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):(H/n).open('xb').write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists();prev=sha(P/'final-receipt.json');assert prev=='0e4a3d4c65cf571aca3743655ba6a72b1631d1e6c0614f5faf21617e61de431b'
pm=load(P/'final-receipt.json');assert len(pm['files'])==89
for x in pm['files']:
 p=R/x['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
t=load(H/'runs-receiver-verified/receipt.json');assert t['status']=='NATIVE_RECEIVER_ACK_SCOPED_PASS_WITH_TWO_ORIGIN_DOMAIN_BOUNDARIES' and t['tests']==9 and len(t['cases'])==41 and t['failures']==t['errors']==0
for n,d in t['source_hashes'].items():assert sha(H/n)==sha(H/'runs-receiver-verified/source-snapshot'/n)==d
cases={x['name']:x['summary'] for x in t['cases']};assert len(cases)==41
for x in cases.values():assert not x['waits'] and x['host_borrowed_FDs_unchanged'] and x['own_C_ACK_precedes_inner_worker']
for n in ['normal-None','normal-reversed-control-order','normal-unpadded-last-rights']:
 x=cases[n];assert x['result']==11 and x['producer']['collector_exit_status']==10752 and x['producer']['own_worker_status']==0 and not x['received_remaining'] and len(x['ack'])==1
for n in ['channel-no-cloexec','socket-stream','no-passcred','bad-peer-creator','named-socket']:assert cases[n]['result']==4 and not cases[n]['received_FDs'] and not cases[n]['ack']
for n in ['253-rights','negative-after-installed-rights','old-HELLO-v1','two-rights']:
 x=cases[n];assert x['result']==2 and not x['received_remaining'] and not x['ack'] and x['producer']['own_worker_status'] is None
assert len(cases['253-rights']['received_FDs'])==253
for n in ['drive-peer-wrong-payload','drive-peer-late-before-ACK','drive-peer-late-after-ACK']:
 x=cases[n];assert x['result']==2 and x['producer_after_parent_return']['own_worker_status'] is None and x['producer_after_parent_return']['collector_exit_status']!=10752
for n in ['malformed-kernel-header','header-copy-fault-after-FD-install','header-copy-fault-without-CTRUNC']:
 x=cases[n];assert x['result']==2 and x['receiver_state']==6 and x['received_remaining'] and x['explicit_incomplete_control_cleanup'] and not x['ack']
x=cases['foreign-origin-boundary'];assert x['result']==11 and x['producer']['collector_exit_status']==9 and x['producer']['own_worker_status'] is None and x['anchor_origin']=='foreign B reused PID after A detached' and any(e.get('A_dead_before_B_active') and e.get('B_distinct_start_tick')==888 for e in x['events'])
x=cases['closed-inner-domain-boundary'];assert x['result']==11 and x['producer']['own_worker_status']==17408 and x['producer']['collector_exit_status']==10752
assert t['actual_parent_C_receives_and_closes_kernel_modeled_FDs'] and t['ACK_required_before_inner_worker'] and t['shared_absolute_expiry_is_still_a_fixed_fixture'] and t['origin_and_closed_domain_not_yet_proven'] and not t['actual_Sony_constructor_clone_anonymous_image_and_plan_binding_implemented'] and t['only_own_ARM64_executed'] and not t['original_Sony_Linux_glibc_or_driver_executed'] and t['new_device_operations']==0 and not t['probe_deployable'] and not t['first_flash_released']
spec=importlib.util.spec_from_file_location('receiver239_seal',H/'receiver_build.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
repro=load(H/'reproducible-build-verified-summary.json');assert repro['status']=='PASS' and repro['source_hashes']==t['source_hashes'] and not repro['deployable']
for role,folder,again,source,digest in [('parent','build-parent-v4','repro-parent-v4','parent_receiver.c','075f36d60f11ba537f6ef2b0515989805407b3dc11c146175501e927c58f25f7'),('collector','build-collector-v2','repro-collector','collector-ack.c','919b38fd7d8ab14b3433579e596fe309a1e2f37ab0328d464d63f10d496b3c5b')]:
 p=H/folder/(role+'.elf');assert sha(p)==sha(H/again/(role+'.elf'))==digest==t[role+'_sha256']==repro[role+'_sha256'] and p.stat().st_size==262144
 seg=D.read_executable(p.read_bytes());assert len(seg)==4 and all(not(x['flags']&1 and x['flags']&2) for x in seg)
 for f in [folder,again]:
  x=load(H/f/'build.json');assert sha(H/f/'source.c')==sha(H/source)==x['source_sha256'] and sha(H/f/'entry.s')==x['entry_source_sha256'] and not x['deployable'] and (H/f/'compiler.stderr.txt').read_bytes()==b''
a=load(H/'SCM-contract.json');assert a['checks']==len(a['check_names'])==44 and len(a['source_ranges'])==6 and a['rights_max']==253 and a['CAP_SYS_ADMIN_sender_can_supply_other_PID_in_reference'] and a['SCM_credentials_alone_are_not_authentic_child_creation_proof'] and not a['header_fault_without_CTRUNC_arithmetic_example']['CTRUNC_condition'] and not a['original_code_executed']
raw=(R/a['original_kernel']).read_bytes();assert sha256(raw).hexdigest()==a['original_kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c';spans=load(H/'original-SCM-spans.json');assert len(spans)==3
for x in spans:
 p=raw[x['start']:x['end']];assert len(p)==x['bytes']==4*len(x['instructions']) and sha256(p).hexdigest()==x['sha256']
 for i,j in enumerate(x['instructions']):assert j['offset']==x['start']+4*i and bytes.fromhex(j['word'])==p[i*4:i*4+4]
for x in a['source_ranges']:
 p=R/x['path'];piece=''.join(p.read_text().splitlines(keepends=True)[x['first_line']-1:x['last_line']]);assert sha(p)==x['sha256'] and sha256(piece.encode()).hexdigest()==x['range_sha256'] and all(s in piece for s in x['required_tokens'])
capture=load(H/'source-capture.json');assert len(capture)==3
for x in capture:assert x['status']=='CAPTURED' and sha(H/x['path'])==x['sha256'] and (H/x['path']).stat().st_size==x['bytes']
for fn in ['source-origin.json','collector-origin.json','builder-origin.json']:
 x=load(H/fn);assert sha(R/x['path'])==x['sha256']
for f in ['runs-receiver-v2','runs-receiver-final','runs-receiver-v3','runs-receiver-v4']:
 x=load(H/f/'receipt.json')
 for n,d in x['source_hashes'].items():assert sha(H/f/'source-snapshot'/n)==d
assert load(H/'runs-receiver-v2/receipt.json')['errors']==1 and load(H/'runs-receiver-v2/receipt.json')['failures']==1
assert load(H/'runs-receiver-v3/receipt.json')['failures']==0 and len(load(H/'runs-receiver-v4/receipt.json')['cases'])==41
old=load(B/'stage235-single-load-preparation-and-exit-observer/remaining-parent-identity-counterexample.json');assert old['must_not_release_this_candidate'] and old['current_false_complete']
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json';assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes();prior=json.loads(before);native=load(H/'native-goal-observed.json');assert native['goal']['status']=='active' and len(prior['requirements'])==16 and not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R));scope=dict(status='OWN_C_PARENT_RECEIVER_ACK_AND_OBJECT_OBSERVER_PASS_WITH_UNPROVEN_ENTRY_ORIGIN',own_checks=9,own_model_cases=41,native_static_checks=44,native_spans=3,source_ranges=6,each_own_ELF_bytes=262144,parent_sha256=t['parent_sha256'],collector_sha256=t['collector_sha256'],own_C_parent_receiver_and_ACK_implemented=True,ACK_precedes_inner_worker_in_scope=True,fixed_synthetic_absolute_expiry_not_actual_plan=True,malformed_or_header_copy_failure_may_leave_unidentified_FDs_UNKNOWN=True,two_origin_and_domain_boundary_counterexamples_retained=True,authentic_Sony_creation_anonymous_image_and_full_plan_binding_proven=False,full_job_resources_or_USB_completion_proven=False,probe_deployable=False,stage235_candidate_unchanged_and_admission_still_failed=True,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,all16_requirements_and_authorizations_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,previous_goal_turn_classification='progress:238 self-proc sender/nonzero exit object observer and 89-member seal',goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=89,tests='runs-receiver-verified/receipt.json',native_contract='SCM-contract.json',conditional_scope_and_unknown_rights_not_overridden=True,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',research_activity='Own C parent receives SCM_RIGHTS/CREDENTIALS, validates dynamic proc FD/current stat, sends exactACK only after checks, closes channel then invokes object observer. Collector now requiresACK before core/worker creation. Protocolv2 shares a fixed synthetic absoluteexpiry, oldv1/lateACKrejected.9checks41cases/two262144B reproducible ELFs;44saved native SCM checks3spans6source ranges pin253FD/CLOEXEC and install-before-header. Reference/native count-only CTRUNC branch allows all-FDs-installed header failure withoutCTRUNC: unidentifiedFDs explicitlyUNKNOWN, no guessed close or clean receipt. CREDENTIALS alone not actual creation proof; legal-boundary model kills/reapsA before foreignB reusesPID with distinctstart and inheritedendpoint assumption; second closed-domain false-complete retained. Actual Sony clone/mask/anonymous image/fullplan/sourcebinding not connected; global admissionunpassed,235unchangedfailed. No device/root;16/formal0.4/0.5/195unchanged.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('239实现父端C接收/目录FD验证/ACK后接对象观察；监管者收到ACK才启内部工作器，协议2用同一绝对期限夹具。9检查41场景和两262144B重复构建通过；44原字检查3范围6源码段固定253/CLOEXEC及先安装后写头，缺CTRUNC也可能有未识别FD，保留UNKNOWN。来源反例改为A先死且回收、B后复用PID且不同起始时间，声明继承端点条件，不虚构同PID并存或内核换FD；内层子域反例仍在。真实创建/匿名存活/完整计划未接，16/195/正式包不变，无设备/root，不能首刷。')
ev=dict(readme=rel+'/README.md',parent=rel+'/parent_receiver.c',collector=rel+'/collector-ack.c',builder=rel+'/receiver_build.py',model=rel+'/model_receiver.py',tests=rel+'/runs-receiver-verified/receipt.json',native_contract=rel+'/SCM-contract.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage239_parent_SCM_anchor_receiver']=ev;new['recovery_parent_SCM_anchor_receiver']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['把239 C接收/ACK/原对象观察与237核心接入实际创建路径：独立clone前信号屏蔽、匿名代码存活、父/子运行时身份、完整准备计划SHA/期限/请求绑定。当前321/5001/53/时间段与关联仍是夹具，静态ELF载体未接Sony构造函数，不投放。','保留两个反例：外来端点持有者在原A死亡回收后以B复用PID发送新HELLO，元数据新起始时间也不是创建身份；内层封闭子域被破坏可误把worker68当0。凭据CAP_SYS_ADMIN路径不能替代端点独占和可信代码/计划关联。','接收错误下先安装FD再头写失败可能无CTRUNC；未识别权利保留UNKNOWN，不猜FD或声称全部资源清理。核对实际接收进程/FD表所有权、错误容纳与Sony服务有界返回；不将局部11充全任务/USB归还。','入口和归还合同闭合后接完整boot采集/主机回传、同机健康备份/独立AP救砖逆写冷启动及MAIN1080p29.97 HEVC42010约16Mbps/exact30/音画长录16项；195root01未批准不启动，正式0.4/0.5及23源码保留。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert prior[key]==new[key]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n';entry='- [2026-10-30 FX3父端目录句柄接收与私有ACK](<'+rel+'/README.md>)：父端C接收/验证/ACK后对象观察，9检查41场景及双端重复构建；44原字核对发现无CTRUNC也可能留未识别FD，保持UNKNOWN。真实创建/匿名代码/完整计划与两个来源/子域前提未闭合；无设备/root，不能首刷。'
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
put('final-receipt.json',dict(schema='fx3-stage239-own-C-parent-receiver-ACK-conditional-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
