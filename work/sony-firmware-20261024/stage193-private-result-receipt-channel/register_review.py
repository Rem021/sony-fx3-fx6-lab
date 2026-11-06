"""Seal this offline implementation; grant no root or camera operation."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,stat,subprocess
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
REL=str(HERE.relative_to(ROOT));PRIOR=BASE/'stage192-global-owner-fence-and-frame-IO'
PRIOR_SHA='1f7a34f67f28c998863b1eed5219597a115dfb05c7491b884b207a4896831079'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def volume():
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(n,v):
 with (HERE/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
volume();assert not (HERE/'final-receipt.json').exists()
assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
prior=json.loads((PRIOR/'final-receipt.json').read_text())
for m in prior['files']:
 p=ROOT/m['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
v=json.loads((HERE/'verification-receipt.json').read_text())
assert v['status']=='PASS_PRIVATE_OWNER_RECEIPT_REVIEW' and v['local_checks']==58
for m in v['files']:
 p=HERE/m['path'];assert p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
b=json.loads((HERE/'build-receipt-v3.json').read_text())
for m in b['sources']:assert digest(HERE/m['path'])==m['sha256']
for m in b['builds'].values():assert digest(Path(m['path']))==m['sha256']
assert not b['native_build_released'] and not b['native_helper_executed']
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(PRIOR/'goal-status-after.json').read_bytes()
old=json.loads(before);new=deepcopy(old);assert len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();new['updated_utc']=now;new['latest_stage']=HERE.name
new['research_activity']='Implemented live kernel-peer ACK barrier and private COMPLETE/HELD receipt over the same owner stream.38 integration plus20 targeted checks pass; native09 remains unreleased/observe-only. Stop or invalid envelope after handshake is checked before owner admission. Shared files cannot substitute for private completion. No root, device, Sony authentication or firmware operation. Full bootstrap/supervisor, restart trust, root cross-UID and real recovery remain.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],
 'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('193完成私有最终结果帧、存活Unix peer ACK及停止复查；38整合+20回执检查=58。共享报告损坏/假完成不能充私有结果，HELD仍保留；接收方拒绝附带FD并关闭副本。原native09仅编译未执行，root跨UID/完整监督与重启后可信回执未验；16要求和全部授权不变，无相机动作。')
evidence={'readme':REL+'/README.md','build':REL+'/build-receipt-v3.json','verification':REL+'/verification-receipt.json',
 'integration':REL+'/integration-results.json','receipts':REL+'/receipt-results.json','limitations':REL+'/implementation-review.json',
 'total_local_checks':58,'private_live_result_delivery_implemented_offline':True,'root_cross_UID_or_actual_camera_validation':False,
 'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0}
new['latest_stage_evidence']['stage193_private_result_receipt_channel']=evidence
new['current_native_owner_channel_candidate']={**evidence,'identifier':'fx3-702-private-receipt-channel-20261029-09',
 'explicitly_approved':False,'native_authentication_scope_released':False,'bootstrap_supervisor_and_global_fence_ready':False,
 'authenticated_final_result_delivery_ready':False,'private_result_transport_implemented_and_same_UID_tested':True,
 'trusted_restart_receipt_ready':False,'same_body_backup_restore_or_independent_rescue_proven':False}
new['next_safe_offline_actions']=[
 '按193契约整合固定bootstrap、Terminal启动与用户监督器；区分relay/helper实际PID，先以kernel身份/路径/hash核验helper再ACK，保存同一peer私有COMPLETE/HELD，不以共享文件或stdout判成功。仅本地代码和假对象，不启动管理员或设备。',
 '补控制器重启后的可信回执核验与保留现场观察；不能仅从用户可改的JSON/bin恢复authenticated标志，不能将UNKNOWN/死PID自动清除或重试。',
 '上述固定代码完成后准备具体可复核的root到UID501、仅主机假对象对照方案及哈希/私有路径；执行仍须新增具体授权。09未批准，旧05已耗，06/07/08不可挪用。',
 '沿用恢复优先：继续同机当前p1获取与受限只读工作器启动、独立boot/updater入口和WBI/真实冷启动研究；不以缺少修改包阻断离线适配，保留全部16项目标。Sony认证、文件/分区读取、模块与任何刷写均不由本轮自动放行。'
]
for key in ('authorization','requirements','prepared_first_device_trial','research_priority'):assert new[key]==old[key]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
index=ROOT/'README.md';ib=index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3私有完成回执与存活握手](<'+REL+'/README.md>)：38项整合＋20项回执检查通过；共享文件不能充最终结果，HELD不释放，原生09未发布/未运行，root跨UID、完整监督和恢复仍待验证，无设备动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (HERE/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS concurrent change'
for dest,data,name in ((canonical,encoded,'.goal.tmp'),(index,ia,'.index.tmp')):
 p=HERE/name
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(p,dest)
members=[];excluded=[]
for p in sorted(HERE.rglob('*')):
 mode=p.lstat().st_mode
 if stat.S_ISLNK(mode):excluded.append({'path':str(p.relative_to(ROOT)),'kind':'symlink not followed','link_text':os.readlink(p)});continue
 if stat.S_ISREG(mode):members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
 elif not stat.S_ISDIR(mode):excluded.append({'path':str(p.relative_to(ROOT)),'mode':oct(mode),'not_opened':True})
put('final-receipt.json',{'schema':'fx3-stage193-private-owner-receipts-v1','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'files':members,'member_count':len(members),'excluded':excluded,'mutable_heads_not_manifest_members':True,
 'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),'local_checks':58,
 'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0,'native_goal_observed':'active',
 'native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(members),'checks':58,
 'native_goal':'active','native_candidate_released_or_executed':False,'new_camera_operations':0,'goal_complete':False}))
