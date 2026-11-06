"""Seal offline fencing work without granting any new root/device operation."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,stat,subprocess
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
REL=str(HERE.relative_to(ROOT));PRIOR=BASE/'stage191-native-owner-channel-integration'
PRIOR_SHA='3d66f1d070a7ff85933b352b87b3c5a39ee5a680a8e9cf3fa30edc99b123f117'
def digest(p):
 h=sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def volume():
 d=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
 if d['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise RuntimeError('wrong volume')
def put(name,value):
 with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
volume();assert not (HERE/'final-receipt.json').exists()
assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
prior=json.loads((PRIOR/'final-receipt.json').read_text())
for m in prior['files']:
 p=ROOT/m['path'];assert not p.is_symlink() and p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
v=json.loads((HERE/'verification-receipt.json').read_text());assert v['local_checks']==56 and v['status']=='PASS_GLOBAL_FENCE_AND_PRIVATE_ENVELOPE_REVIEW'
for m in v['files']:
 p=HERE/m['path'];assert p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
b=json.loads((HERE/'build-receipt-v2.json').read_text())
for m in b['sources']:assert digest(HERE/m['path'])==m['sha256']
for m in b['builds'].values():assert digest(Path(m['path']))==m['sha256']
assert not b['native_build_released'] and not b['native_helper_executed']
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(PRIOR/'goal-status-after.json').read_bytes()
old=json.loads(before);new=deepcopy(old);assert len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();new['updated_utc']=now;new['latest_stage']=HERE.name
new['research_activity']='Implemented cooperative cross-process journal fence and removed user-backed mmap from privileged entry.38 process integration plus18 journal checks pass; no root/native device execution.OWNED/UNKNOWN persists after PID death;CLEAN alone permits next instance. Truncated/aliased envelope cannot kill pending private owner. Native08 unreleased/observe-only. Authenticated completion, bootstrap/supervisor and real root/device validation remain.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].extend([
 '192新增合作controller跨进程flock+256B追加SHA链日志，OWNED/UNKNOWN不会因PID死或内核锁释放自动放行；CLEAN只由当前私有无调用/已清理结果产生。不同grant、竞争、死PID与损坏/满额拒绝均有本机实测。',
 '192管理员入口复制4096B后以pread/pwrite处理报告/停止意图，不再mmap用户文件；文件截断/别名/I/O异常设置停止且不释放未返回调用。真实进程截断等待中的假调用，后续实例被拒，假测试结束清理调用为0。',
 '192最终38项整合+18项日志共56本地检查通过，ASan/UBSan；底层wire/session与191逐字节相同，旧55项未重跑未计入本轮。原生08候选FX3_NATIVE_RELEASED=0且observe-only，无管理员/相机调用。',
 '192可信最终回执仍须经核对的socket传输，启动/用户监督器未迁移；root跨UID/私有日志、真实协议/备份/恢复未验。原16项及授权原样保留，目标未缩小。',
])
evidence={'readme':REL+'/README.md','build':REL+'/build-receipt-v2.json','verification':REL+'/verification-receipt.json',
 'integration':REL+'/integration-results.json','journal':REL+'/guard-results.json','limitations':REL+'/implementation-review.json',
 'total_local_checks':56,'cooperative_cross_process_fence_implemented_offline':True,
 'root_protected_fence_or_actual_camera_validation':False,'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0}
new['latest_stage_evidence']['stage192_global_fence_and_private_frame_IO']=evidence
new['current_native_owner_channel_candidate']={**evidence,'identifier':'fx3-702-global-owner-channel-20261029-08',
 'explicitly_approved':False,'native_authentication_scope_released':False,'bootstrap_supervisor_and_global_fence_ready':False,
 'authenticated_final_result_delivery_ready':False,'same_body_backup_restore_or_independent_rescue_proven':False}
new['next_safe_offline_actions']=[
 '仅本机代码：以192私有frame和持久排他契约完成经kernel peer核对socket上的私有最终结果帧；持有UNKNOWN必须可报告但不能自动释放。随后迁移固定bootstrap/Terminal/用户监督器，按新08候选核对哈希、PID出生时间和全局日志，不启动管理员/helper/设备动作。',
 '完成上述具体固定代码后再准备root到UID501的仅主机/假设备对照方案；同UID56项不能代替root跨UID或真实IOKit。保留Sony模式迁移、鉴权退出、当前p1读取/备份/独立恢复与主录验收缺口。',
]+old['next_safe_offline_actions']
for key in ('authorization','requirements','prepared_first_device_trial','research_priority'):assert new[key]==old[key]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
index=ROOT/'README.md';ib=index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3跨实例排他与私有报告I/O](<'+REL+'/README.md>)：38项整合＋18项日志通过；死PID/UNKNOWN不自动放行，报告截断不释放等待中的owner；原生08未发布/未运行，可信回执与启动监督待补，无设备动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (HERE/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS concurrent change'
for destination,data,name in ((canonical,encoded,'.goal.tmp'),(index,ia,'.index.tmp')):
 p=HERE/name
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(p,destination)
members=[];excluded=[]
for p in sorted(HERE.rglob('*')):
 mode=p.lstat().st_mode
 if stat.S_ISLNK(mode):excluded.append({'path':str(p.relative_to(ROOT)),'kind':'own adversarial symlink fixture','link_text':os.readlink(p),'not_followed':True});continue
 if stat.S_ISREG(mode):members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
 elif not stat.S_ISDIR(mode):excluded.append({'path':str(p.relative_to(ROOT)),'kind':'own adversarial nonregular fixture','mode':oct(mode),'not_opened':True})
put('final-receipt.json',{'schema':'fx3-stage192-global-fence-and-private-envelope-v1','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'files':members,'member_count':len(members),'excluded':excluded,'mutable_heads_not_manifest_members':True,
 'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),
 'local_checks':56,'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0,
 'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(members),'excluded_own_fixtures':len(excluded),'checks':56,
 'native_goal':'active','native_candidate_released_or_executed':False,'new_camera_operations':0,'goal_complete':False}))
