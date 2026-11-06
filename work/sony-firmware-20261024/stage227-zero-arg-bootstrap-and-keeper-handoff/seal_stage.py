"""Verify existing offline receipts and bind the completed stage, never run a target."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime, timezone
import ast, json, os, plistlib, stat, subprocess
H=Path(__file__).resolve().parent; B=H.parent; R=H.parents[2]; P=B/'stage226-static-keeper-and-parent-image-contract'; T=R/'outputs/fx3-recovery-adapter'
def sha(p): return sha256(p.read_bytes()).hexdigest()
def enc(v): return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,v): (H/n).open('xb').write(enc(v))
def volume(): assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume(); assert not (H/'final-receipt.json').exists()
prev=sha(P/'final-receipt.json'); assert prev=='0b8b05826f4befef362f974452d0be05f1d16d266fa9377b8384b08b4f638c5d'
pm=json.loads((P/'final-receipt.json').read_text()); assert len(pm['files'])==1282
for row in pm['files']:
 p=R/row['path']; assert not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
r=json.loads((H/'runs-final/receipt/results.json').read_text()); assert r['status']=='PASS' and r['tests_run']==6 and not r['failures'] and not r['errors'] and not r['details'] and r['all_model_threads_terminal'] and len(r['cases'])==10
for n,d in {**r['source_hashes'],**r['build']['source_pins']}.items(): assert sha(H/n)==d,n
digest='96939f5ac7cfb64da3866c710cf511e13515f806415a9ab37beab80c1d3940eb'
assert sha(H/'runs-final/built/parent-module.so')==sha(H/'reproducible-build/parent-module.so')==r['build']['sha256']==digest
assert r['build']['bytes']==262936 and set(r['build']['exports'])=={'fx3_bootstrap_step','fx3_bootstrap_status'}
cases={c['name']:c for c in r['cases']}; assert len(cases)==10
for c in cases.values(): assert not c['constructor_syscalls'] and c['zero_argument_calls_use_poisoned_x0_x7'] and c['parent_FD_flags_unchanged'] and not c['parent_errors']
for n in ['startup','one-job','full']: assert cases[n]['state']==3 and cases[n]['keeper_return']==0
for n in ['bad-plan','missing-plan','image-byte','non-main-thread']: assert cases[n]['state']==4 and not cases[n]['clones']
assert cases['keeper-close']['keeper_return']==89 and cases['keeper-close']['state']==2 and cases['keeper-close']['results'][-1]['state']==0
assert cases['outer-reaper']['state']==2 and cases['outer-reaper']['keeper_return']==0 and any(w['returned']==-10 for w in cases['outer-reaper']['waits'])
assert cases['new-loader']['state']==2 and not cases['new-loader']['clones']
assert sum(c['keeper_return'] is not None for c in cases.values())==5 and sum(len(c['worker_returns']) for c in cases.values())==7
assert cases['full']['source_reads']==[128,128,128,126]
assembled=H/'runs-final/assembled/source.boot1'; assert assembled.stat().st_size==33423360 and sha(assembled)=='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
failed=[]
for name in ['runs-first','runs-clock-fixed','runs-FD-fixed']:
 q=json.loads((H/name/'receipt/results.json').read_text()); assert q['status']=='FAIL'
 for n,d in q['source_hashes'].items(): assert sha(H/name/'source-snapshot'/n)==d
 failed.append(dict(run=name,tests=q['tests_run'],failures=q['failures'],errors=q['errors'],receipt_sha256=sha(H/name/'receipt/results.json')))
assert not r['Sony_loader_or_Linux_kernel_executed'] and not r['flashable'] and not r['new_camera_operations']
cap=json.loads((H/'ABI-source-capture.json').read_text()); assert cap['returncode']==0 and sha(H/cap['path'])==cap['sha256']
references=[P/'runs-final/keeper-built/worker.elf',P/'runs-final/worker-built/worker.elf',B/'stage224-controlled-launcher-and-preexec-image-pin/core_support.inc']
assert sha(references[0])=='93bcd77751550c7079a38dfe532272ecf71d849f906c4b05d5515267fa888581' and sha(references[1])=='349115672da2bc494e073472446004ee476c77ecc716756351cfe50a395b66e7' and references[2].read_bytes()==(H/'core_support.inc').read_bytes()
release=json.loads((B/'stage215-AP-boot-capture-worker-candidate/release-receipt.json').read_text()); assert len(release['files'])==23 and sha(R/release['archive'])==release['archive_sha256']
for row in release['files']: assert sha(T/row['path'])==row['sha256']
assert sha(T/'releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
assert sha(B/'stage195-root-host-validation-plan/approval-bundle.json')=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0' and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
for p in H.rglob('*.py'): ast.parse(p.read_text(),filename=str(p))
before=(H/'goal-status-before.json').read_bytes(); canonical=B/'GOAL_STATUS.json'; assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before); native=json.loads((H/'native-goal-observed.json').read_text()); assert native['goal']['status']=='active' and len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat(); rel=str(H.relative_to(R))
scope=dict(status='PASS_OWN_ZERO_ARGUMENT_BOOTSTRAP_CHAIN_ONLY',tests_passed=6,scenarios=10,bootstrap_instances=10,keeper_instances=5,worker_instances=7,all_model_threads_terminal=True,bootstrap_sha256=digest,reproducible_binary_identical=True,full_synthetic_bytes=33423360,native_loader_path_or_repeated_dispatch_or_host_return_implemented=False,outer_im_reaper_race_solved=False,outer_reaper_ECHILD_retains_HELD=True,FINISH0_exit89_retains_HELD=True,actual_camera_backup_or_independent_recovery_verified=False,new_camera_USB_cache_root_auth_upload_or_write_operations=0,all16_requirements_unchanged=True,formal23_sources_release04_05_unchanged=True,root195_pending_unlaunched=True,goal_complete=False,persistent_write_release=False)
put('verification-receipt.json',dict(schema='fx3-stage227-offline-bootstrap-verification-v1',created_utc=now,previous_manifest_sha256=prev,previous_members_reverified=1282,**scope))
put('source-derivation.json',dict(active_source_pins=r['build']['source_pins'],references=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in references],failed_runs=failed,model_fixes='shared monotonic target clock, no inherited descriptor reuse, fixture namespaces disambiguated; no C guard relaxation',code_fixes='duplicate enum removal, explicit volatile iovec stores, owner collision remains HELD without probing unowned FD',original_Sony_code_executed=False))
new=deepcopy(old); new.update(updated_utc=now,latest_stage=H.name,research_activity='Own no-arg bootstrap executes explicit step/status with fixed1536B RAM plan, full keeper/worker image pins, sticky global owner, cloned3FD keeper and private512B tasks/results plus exact wait4.6checks/10cases pass on own ARM64/fakeLinux;4window33423360B synthetic assembly. FINISH0/exit89 and outer im reaper ECHILD remain HELD; new loader cannot reclaim. Native loader path/repeated dispatcher/host return remain unimplemented; no camera backup/recovery/flash proof.',goal_manager_status='active',goal_manager_status_last_observed='active')
new['progress_audit']['classification']='progress'; new['progress_audit']['previous_goal_turn_classification']='progress:226 standalone keeper and v2worker contract'
new['progress_audit']['basis'].append('227补零参数启动桥、自写三程序链与真实缺口反例：6检查/10模拟场景完成，重复构建逐字节一致；原厂加载路径/重复调度/主机回传与外层im回收竞争仍缺，不能首刷。重启后读取既有终态回执未重跑测试，无设备/root动作。')
ev=dict(readme=rel+'/README.md',verification=rel+'/verification-receipt.json',tests=rel+'/runs-final/receipt/results.json',bootstrap_sha256=digest,scope=scope)
new['latest_stage_evidence']['stage227_zero_arg_bootstrap']=ev; new['recovery_zero_arg_bootstrap_and_keeper_handoff']=ev
new['current_native_goal_observation']=dict(receipt=rel+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['next_safe_offline_actions']=['先核对真实FX3原厂加载入口的路径/符号来源、主线程及重复调度；自写零参数模块不证明可达，不再用包装层累积代替加载证据。','核对最新A7CII/REA及BootROM恢复源码的具体提交和适用机型；区分主系统依赖与独立硬件恢复，不直接套载荷/偏移。','外层im可抢先回收看护退出；保持UNKNOWN及原占用，不改原厂信号、不凭FINISH/PID消失成功、不自动重试。','16要求、同机健康完整备份/真实访问归还/独立AP救砖/逆写冷启动和主录文件验收保持；195仅主机root01未获具体批准且不启动或重问。']
for key in ['authorization','requirements','prepared_root_host_trial','prepared_first_device_trial','research_priority']: assert new[key]==old[key]
index=R/'README.md'; ib=index.read_bytes(); marker='## 相机与固件研究\n'; entry='- [2026-10-30 FX3零参数启动桥与看护交接候选](<'+rel+'/README.md>)：6检查/10模拟场景通过，自写三程序链及四窗口人工源组装、重复构建一致；FINISH0后exit89及外层im抢先回收均保持UNKNOWN。真实加载/重复调度/主机回传及独立恢复未验，无设备动作，尚不能首刷。'
assert ib.decode().count(marker)==1 and entry not in ib.decode(); ia=ib.decode().replace(marker,marker+'\n'+entry+'\n',1).encode(); after=enc(new)
(H/'goal-status-after.json').open('xb').write(after);(H/'readme-rebased-before.md').open('xb').write(ib);(H/'readme-after.md').open('xb').write(ia)
volume(); assert canonical.read_bytes()==before and index.read_bytes()==ib
for dst,data in [(canonical,after),(index,ia)]:
 tmp=H/('.'+dst.name+'.tmp')
 with tmp.open('xb') as f: f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,dst)
members=[]
for p in sorted(H.rglob('*')):
 s=p.lstat()
 if stat.S_ISDIR(s.st_mode): continue
 assert stat.S_ISREG(s.st_mode) and not p.is_symlink(); members.append(dict(path=str(p.relative_to(R)),bytes=s.st_size,sha256=sha(p)))
put('final-receipt.json',dict(schema='fx3-stage227-noarg-bootstrap-seal-v1',created_utc=now,previous_manifest_sha256=prev,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),**scope))
print(json.dumps(dict(status='SEALED_OFFLINE_CANDIDATE_ONLY',members=len(members),manifest_sha256=sha(H/'final-receipt.json'),tests=6,scenarios=10,first_flash_released=False)))
