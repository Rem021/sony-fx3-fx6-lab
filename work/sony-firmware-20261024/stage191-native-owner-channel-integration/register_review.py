"""Seal local implementation; never release root/device/protocol/flash work."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
REL=str(HERE.relative_to(ROOT));PRIOR=BASE/'stage190-AP-process-launch-and-loader'
PRIOR_SHA='291c4e26ff2858ffcdf3ec005441152bc363df6dce61efc847e48b31d688b7c4'
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
v=json.loads((HERE/'verification-receipt.json').read_text())
assert v['status']=='PASS_NATIVE_OWNER_CHANNEL_OFFLINE_INTEGRATION_REVIEW' and v['total_local_checks']==87
for m in v['files']:
 p=HERE/m['path'];assert p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
b=json.loads((HERE/'build-receipt-v5.json').read_text())
for m in b['sources']:assert digest(HERE/m['path'])==m['sha256']
for m in b['builds'].values():assert digest(Path(m['path']))==m['sha256']
assert not b['native_build_released'] and not b['native_helper_executed']
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(PRIOR/'goal-status-after.json').read_bytes()
old=json.loads(before);new=deepcopy(old);assert len(old['requirements'])==16
now=datetime.now(timezone.utc).isoformat();new['updated_utc']=now;new['latest_stage']=HERE.name
new['research_activity']='Implemented ABI4/schema3 same-process native owner/channel candidate with real pipe-map retention, kernel peer PID/UID/birth checks, private decision/deadline/result storage and retained lifetime after START/unknown calls.32 real-process fake-object integration checks +55 wire regressions pass;2 inert flows. Native entry is unreleased and additionally observe-only. No root/device execution, backup or recovery proof. Bootstrap/supervisor/global fence remain.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].extend([
 '191把通信阶段接到原owner接口核验后，同进程借用原IOKit650对象并保留真实pipe索引；owner ABI4/entry schema3，新07候选未批准且原生入口FX3_NATIVE_RELEASED=0，另原生仅observe/status/end。',
 '191以Unix stream固定长度帧和真实内核peer UID/PID/出生时间核对观察者，连接核对早于owner设备调用；配置/目标快照/预算/保留判断移入私有内存，公开报告改动不驱动清理。',
 '191任何START后即便STOP返回仍保留owner和底层存储；同步调用阻塞时无自动关闭、取消、重置或重试。真观察进程退出时假OUT继续，显式放行后无IN且三项清理为0；不是相机线程退出或实机恢复。',
 '191最终32项真实进程+55项底层回归共87项通过，另2纯夹具流程；helper有ASan/UBSan，原生候选仅编译未执行。初始假时钟拒绝、辅助FD残留和镜像时序断言失败均保留并修复。',
 '191仍缺固定启动/监督器/受保护交付迁移、跨grant全局排他、root跨UID实证、真实协议/读回/备份/恢复；共享映射采用协作观察者模型，不声明完整恶意客户端隔离。16项要求和所有授权保留。',
])
evidence={'readme':REL+'/README.md','build':REL+'/build-receipt-v5.json','verification':REL+'/verification-receipt.json',
 'integration':REL+'/integration-results.json','wire_regression':REL+'/wire-regression/results.json','limitations':REL+'/implementation-review.json',
 'total_local_checks':87,'inert_flows':2,'owner_ABI':4,'entry_schema':3,
 'root_peer_or_actual_camera_validation':False,'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0}
new['latest_stage_evidence']['stage191_native_owner_channel_integration']=evidence
new['current_native_owner_channel_candidate']={**evidence,'identifier':'fx3-702-native-owner-channel-20261029-07','explicitly_approved':False,
 'native_authentication_scope_released':False,'bootstrap_supervisor_and_global_fence_ready':False,'same_body_backup_restore_or_independent_rescue_proven':False}
new['next_safe_offline_actions']=[
 '仅本机实现：以191 ABI4/schema3接续固定Terminal/bootstrap和用户监督器/受保护结果交付，补跨未来grant/进程的全局排他和UNKNOWN阻塞占用处理；不复用已消耗05授权，不启动原生helper/管理员/相机调用。',
 '核对191协作共享映射的寿命边界，按实际监督器契约设计root跨UID的仅主机对照候选；先完成具体代码/固定SHA和范围再请求任何新增动作。真实MSC转SERVICE、鉴权退出与同机固定读取准入继续待证。',
]+old['next_safe_offline_actions']
for key in ('authorization','requirements','prepared_first_device_trial','research_priority'):assert new[key]==old[key]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
index=ROOT/'README.md';ib=index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3原生owner与有界通道整合候选](<'+REL+'/README.md>)：32项进程整合＋55项底层回归通过；私有状态、同进程借用、peer身份和UNKNOWN保留已接线，原生入口未发布/未运行，启动监督与全局排他待补，无设备动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (HERE/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS concurrent change'
for destination,data,name in ((canonical,encoded,'.goal.tmp'),(index,ia,'.index.tmp')):
 p=HERE/name
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(p,destination)
members=[]
for p in sorted(HERE.rglob('*')):
 assert not p.is_symlink(),p
 if p.is_file():members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
put('final-receipt.json',{'schema':'fx3-stage191-native-owner-channel-offline-v1','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'files':members,'member_count':len(members),'mutable_heads_not_manifest_members':True,
 'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),
 'local_checks':87,'inert_flows':2,'native_candidate_released_or_executed':False,'new_administrator_or_camera_operations':0,
 'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(members),'checks':87,
 'native_goal':'active','native_candidate_released_or_executed':False,'new_camera_operations':0,'goal_complete':False}))
