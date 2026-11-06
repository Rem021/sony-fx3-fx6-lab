"""Seal actual own entry/preparation changes; keep all device gates open."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage241-public-recovery-delta-and-first-entry-gaps';T=R/'outputs/fx3-recovery-adapter'
def load(p):return json.loads(p.read_text())
def sha(p):return sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v):
 with (H/n).open('xb') as f:f.write(enc(v))
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
prev=sha(P/'final-receipt.json');assert prev=='5d69c8b6418fa694e5d4a37652099bc5b1f266597b7074d3427c2005892a9d32'
pm=load(P/'final-receipt.json');assert len(pm['files'])==23
for x in pm['files']:
 p=R/x['path'];assert p.is_file() and not p.is_symlink() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
a=load(H/'candidate-audit.json');assert a['status']=='OWN_DYNAMIC_ENTRY_PLAN2_IPC4_CLAIM_SCOPED_PASS_NOT_DEVICE_ADMISSION'
assert a['tests']==9 and a['model_cases']==44 and a['link_relocations']==215 and a['uniform_rebase_arithmetic_checks']==1075
assert len(a['source_ranges'])==5 and len(a['malformed_dynamic_rejections'])==3
t=load(H/'runs-v2/receipt.json');assert t['tests']==9 and len(t['cases'])==44 and t['failures']==t['errors']==0
assert t['status']=='OWN_DT_INIT_PREPARATION_AND_CROSS_LOAD_CLAIM_SCOPED_PASS'
assert t['only_own_ARM64_executed'] and t['all_Linux_VFS_IPC_process_signal_time_and_loader_entry_are_explicit_models']
assert t['new_device_operations']==0 and not t['actual_Sony_dlopen_controller_authorization_namespace_and_host_return_verified']
assert not t['full_boot_reader_integrated'] and not t['probe_deployable'] and not t['first_flash_released']
for n,pin in t['source_hashes'].items():assert sha(H/n)==sha(H/'runs-v2/source-snapshot'/n)==pin
assert t['source_hashes']==a['test_source_hashes']
for folder in ['build-v2','reproducible-v2']:
 p=H/folder/'entry.so';b=load(H/folder/'build.json')
 assert sha(p)==b['sha256']==t['binary_sha256']==a['full_file_sha256']=='e6fc7398b05939c40150471c216ddef2e0a15c9cf01d6c0d83ccebd6218807ff'
 assert p.stat().st_size==262144 and b['immutable_image_id']==t['immutable_image_id']!=t['binary_sha256']
 assert b['ET_DYN_DT_INIT_zero_argument_entry_present'] and b['dynamic_inspection']['DT_INIT']==b['global_offsets']['fx3_entry_init']
 assert not b['has_imports_or_runtime_relocations'] and not b['deployable']
 for n,pin in b['source_pins'].items():assert sha(H/n)==sha(H/folder/n)==pin
 for n in ['parent','collector','bridge','front']:assert not (H/folder/(n+'.o.stderr.txt')).read_bytes()
cases={x['name']:x['summary'] for x in t['cases']};assert len(cases)==44
for n in ['normal-321','normal-9011','normal-90','direct-DT_INIT-target']:
 s=cases[n];assert s['result']==11 and s['collector_status']==10752 and s['worker_status']==0 and s['collector_reaped']
 assert not s['root_remaining_new_FDs'] and not s['root_remaining_anonymous'] and s['final_mask']==s['original_mask']
for s in cases.values():assert s['borrowed_FDs_unchanged'] and not s['source_accesses']
for n in ['fresh-after-None','fresh-after-short-plan-write','fresh-after-post-publish-root-close']:
 assert cases[n]['result']==2 and not cases[n]['clones']
for n in ['interleaved-nonce-False','interleaved-nonce-True']:
 assert cases[n]['result']==11 and [x['result'] for x in cases[n]['claims']]==[0,-17]
 assert len(cases[n]['other_results'])==1 and not cases[n]['other_results'][0]['clones']
assert cases['mutable-padding-boundary']['result']==11 and cases['mutable-padding-boundary']['observed_image_file_sha256']!=t['binary_sha256']
assert cases['bridge-mask-restore-error']['result']==2 and cases['bridge-mask-restore-error']['final_mask']!=cases['bridge-mask-restore-error']['original_mask']
for x in a['source_ranges']:
 p=R/x['path'];piece=''.join(p.read_text().splitlines(keepends=True)[x['first_line']-1:x['last_line']])
 assert sha(p)==x['sha256'] and sha256(piece.encode()).hexdigest()==x['range_sha256'] and all(v in piece for v in x['required_tokens'])
for folder in ['runs-integrated','runs-verified']:
 r=load(H/folder/'receipt.json')
 for n,pin in r['source_hashes'].items():assert sha(H/folder/'source-snapshot'/n)==pin
assert load(H/'runs-integrated/receipt.json')['failures']==1 and load(H/'runs-verified/receipt.json')['failures']==0
for origin in load(H/'source-origins.json'):assert sha(R/origin['path'])==origin['sha256']
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
release=load(B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json');assert len(release['files'])==23
for x in release['files']:assert sha(T/x['path'])==x['sha256']
assert sha(R/release['archive'])==release['archive_sha256']=='fd2130628b62939e867c7fad5887277d07d06bbd8ee41aeb1c793c22bd71bee4'
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
before=(H/'goal-status-before.json').read_bytes();canonical=B/'GOAL_STATUS.json'
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
prior=json.loads(before);native=load(H/'native-goal-observed.json')
assert native['goal']['status']=='active' and len(prior['requirements'])==16
assert not prior['goal_complete'] and not prior['persistent_write_release']
now=datetime.now(timezone.utc).isoformat();rel=str(H.relative_to(R))
scope=dict(status=a['status'],own_checks=9,own_model_cases=44,own_ELF_bytes=262144,
 full_file_sha256=t['binary_sha256'],immutable_image_id=t['immutable_image_id'],
 own_ET_DYN_DT_INIT_entry_preparer_and_bridge_integrated=True,
 complete_plan2_and_IPC4_bind_file_SHA_length_and_normalized_image_ID=True,
 shared_namespace_sticky_claim_cross_reload_and_nonce_interleavings_modeled=True,
 real_global_namespace_endpoint_exclusivity_and_no_external_claim_removal_proven=False,
 actual_Sony_RTLD_request_authentication_and_host_result_return_verified=False,
 runtime_mutable_page_not_authenticated_by_normalized_ID_boundary_retained=True,
 mask_restore_failure_leaves_changed_state_HELD=True,
 source_ranges=5,link_relocations=215,rebase_arithmetic_checks=1075,
 full_boot_capture_independent_AP_restore_and_MAIN_HEVC_verified=False,
 probe_deployable=False,new_device_USB_cache_admin_auth_upload_or_firmware_writes=0,
 original_Sony_glibc_Linux_driver_or_public_camera_code_executed=False,
 formal23_sources_release04_05_unchanged=True,all16_requirements_and_authorizations_unchanged=True,
 root195_pending_unlaunched=True,previous_goal_turn_classification='progress:241 changed public HEAD exact document-only delta and240 readback sealed',
 goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=23,**scope))
new=deepcopy(prior);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',
 research_activity='Own262144B ET_DYN DT_INIT candidate integrates234 private plan preparation with240 anonymous-clone/SCM/object-exit bridge. Plan2/IPC4 bind full source-fileSHA+length AND normalized immutable imageID/fullplanSHA; distinct hashes explicit. Sticky0700 fixed RAM preparation-directory claim gates healthy/failed fresh loads and interleaved different nonces under same shared VFS assumptions.9checks44fake-kernel cases, identicalv2builds,215relocations1075rebase checks,3malformed dynamic rejections,5upstream source ranges. Oldwrong-offset RWnegative test retained/corrected with explicit mutable-padding acceptance boundary; runtimeID is not file/request authentication. Actual Sony RTLD/namespace/body/controller/hostreturn and original signals/cache/stack/time still unverified, mask-restore fault remains changed-stateHELD. No fullboot worker/device/root. All16/formal23/0.4/0.5/195unchanged; firstflash not released.')
new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']=scope['previous_goal_turn_classification']
new['progress_audit']['basis'].append('242实现带DT_INIT的ET_DYN：完整私有计划准备与240监管桥同次接通；计划2/IPC4同时绑定完整文件SHA/长度、规范化运行ID和完整计划SHA。固定RAM目录阻止健康/失败后的新加载及不同nonce交错，仍限同命名空间/无人外删。9检查44模型场景、重复262144B构建、215引用1075算术及5源码段通过。错误注入落RW页的旧失败保留，显式保留RW不受运行ID认证边界。真实Sony加载/可信控制端/同机与回传/恢复仍缺，掩码恢复失败保持改变状态HELD；无设备/root，全部16/195/正式包不变，不能首刷。')
ev=dict(readme=rel+'/README.md',front=rel+'/front.c',bridge=rel+'/bridge.c',builder=rel+'/entry_build.py',
 model=rel+'/model_entry.py',tests=rel+'/runs-v2/receipt.json',audit=rel+'/candidate-audit.json',verification=rel+'/verification-receipt.json',scope=scope)
new['latest_stage_evidence']['stage242_DT_INIT_preparation_cross_load_claim']=ev
new['recovery_DT_INIT_preparation_cross_load_claim']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=[
 '将242完整文件SHA/长度、计划2/IPC4及运行时ID接入可信控制端请求和同机授权绑定；当前人工nonce/profile/controller和im文件哈希仅关联，不证明目标身体或请求授权。不投放/认证/启动195。',
 '补真实setter/加载返回合同与主机结果回传；DT_INIT存在/模型进入不充Sony dlopen接受或USB归还。核对实际全局tmpfs/命名空间/共享端点与占位所有权，保留239来源/子域、未知权利和掩码恢复失败边界；不自动删除占位或把状态11当全任务完成。',
 '前置入口/归还合同闭合后整合完整boot采集与主机回传、同机健康备份及独立AP救砖/逆写逐字节核对冷启动；MAIN1080p29.97 HEVC42010约16Mbps/exact30/实际文件音画长录等16项须全部完成。正式0.4/0.5与23源码和195待批准状态保留。']
for k in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']:assert new[k]==prior[k]
index=R/'README.md';ib=index.read_bytes();marker='## 相机与固件研究\n'
entry='- [2026-10-30 FX3构造入口与跨加载占位候选](<'+rel+'/README.md>)：DT_INIT共享库接完整准备器与监管桥，计划2/IPC4绑定完整文件与运行ID；9检查44模型场景、重复构建和215引用1075核对通过。同命名空间保留式占位拒绝重载/换nonce，真实Sony加载/授权/回传及恢复未验；无设备/root，不能首刷。'
assert ib.decode().count(marker)==1 and entry not in ib.decode()
ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode();after=enc(new)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
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
put('final-receipt.json',dict(schema='fx3-stage242-own-DT-INIT-plan2-IPC4-cross-load-claim-seal-v1',created_utc=now,
 previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
 goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status=scope['status'],members=len(members),manifest_sha256=sha(H/'final-receipt.json'),first_flash_released=False)))
