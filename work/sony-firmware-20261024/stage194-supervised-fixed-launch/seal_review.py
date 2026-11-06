"""Verify and seal offline launch work. Never execute helpers or grant access."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from copy import deepcopy
import json,os,plistlib,re,stat,subprocess,sys,zipfile
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
REL=str(HERE.relative_to(ROOT));PRIOR=BASE/'stage193-private-result-receipt-channel'
PRIOR_SHA='0f7003ae6081b585c9b03254a4e5a5f6b5e5ceb28f4a906effd1a40f4fb3f01e'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(name,value):
 with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (HERE/'final-receipt.json').exists()
assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
prior=json.loads((PRIOR/'final-receipt.json').read_text())
for m in prior['files']:
 p=ROOT/m['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==m['bytes'] and digest(p)==m['sha256']
for m in json.loads((HERE/'source-before.json').read_text()):assert digest(ROOT/m['source'])==m['sha256']
for name in ('build-receipt.json','build-receipt-v2.json'):
 b=json.loads((HERE/name).read_text());assert not b['native_build_released'] and not b['native_helper_executed']
 for m in b['builds'].values():assert digest(Path(m['path']))==m['sha256']
 for k in ('fixture','ipc'):assert 'IOKit.framework' not in b['builds'][k]['dependencies'] and 'libusb' not in b['builds'][k]['dependencies']
 if name=='build-receipt-v2.json':
  for m in b['sources']:assert digest(HERE/m['path'])==m['sha256']
 else:
  with zipfile.ZipFile(HERE/'initial-compiled-sources.zip') as z:
   for m in b['sources']:assert sha256(z.read(m['path'])).hexdigest()==m['sha256']
report=json.loads((HERE/'supervisor-results.json').read_text());chunk=json.loads((HERE/'incremental-stream-result.json').read_text())
assert report['status']=='PASS_FIXED_LAUNCH_SUPERVISOR' and report['tests_run']==16 and all(m['status']=='PASS' for m in report['results'])
assert chunk['status']=='PASS_INCREMENTAL_SAME_STREAM' and chunk['tests_run']==1
assert report['test_source_sha256']==digest(HERE/'test_supervisor.py')
assert report['build_receipt_sha256']==digest(HERE/'build-receipt-v2.json')
for name,h in report['python_sources'].items():assert digest(HERE/name)==h
for key,file in (('test_source_sha256','test_incremental_stream.py'),('supervisor_source_sha256','supervisor.py'),('receiver_source_sha256','receipt_receiver.py')):
 assert chunk[key]==digest(HERE/file)
assert not report['native_helper_executed'] and report['root_or_administrator_operations']==report['real_device_operations']==0
same=['owner_core.c','owner_iokit.c','owner_channel.c','owner_channel.h','iokit_wire.c','iokit_wire.h','native_session.c','native_session.h',
      'global_guard.c','global_guard.h','frame_io.c','frame_io.h','owner_trial.h','owner_fixture.c','fake_iokit.c','entry_shared.h','entry_support.c','owner_ipc.c']
for name in same:assert (HERE/name).read_bytes()==(PRIOR/name).read_bytes()
assert '#define FX3_NATIVE_RELEASED 0' in (HERE/'entry_target.h').read_text()
entry=(HERE/'owner_entry_main.c').read_text();assert 'fx3_helper_hello(' in entry and 'pre_owner_ready(&context)' in entry and 'for(;;)pause_short();' in entry
assert 'mmap(' not in (HERE/'controller_ipc.py').read_text()
ps=subprocess.check_output(['/bin/ps','-axo','command='],text=True)
assert not any(str(HERE) in x and ('/owner-fixture-helper' in x or '/owner-native-helper' in x or '/Fixture.command' in x) for x in ps.splitlines()),'fixture process still live'
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(PRIOR/'goal-status-after.json').read_bytes()
old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
now=datetime.now(timezone.utc).isoformat()
put('primary-source-review.json',{'checked_utc':now,'sources':[
 {'url':'https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/open.2.html','scope':'Apple archived open flags; exclusive no-follow semantics; local SDK/build and actual tests are this-host evidence'},
 {'url':'https://docs.python.org/3/library/time.html#time.monotonic','scope':'official platform clock implementation background; rendered docs currently3.15, local runtime and measured offset recorded separately'},
 {'url':'https://github.com/YuuLuo/a7c2-camera-tools','scope':'repository identity/model scope refreshed; no latest HEAD digest obtained'},
 {'url':'https://github.com/QAQLeonard/a7c2-fl23-research','scope':'repository identity/A7CII2.01 scope refreshed; no new FX3 compatibility assertion'}],
 'GitHub_HEAD_API_check':'both commit/main URLs inaccessible through web tool; not claimed unchanged or current-pinned',
 'local_python':sys.version,'local_clock_evidence':'clock-observation.json','root_or_camera_operations':0})
put('implementation-review.json',{'status':'FIXTURE_LAUNCH_SUPERVISION_AND_SELF_HELLO_IMPLEMENTED_OFFLINE',
 'candidate':'fx3-702-supervised-owner-20261029-10','local_checks':17,'full_fixture_flows':16,'incremental_real_stream':1,
 'native_helper_released_or_executed':False,'new_root_or_camera_operations':0,'root_cross_UID_tested':False,
 'root0500_hash_policy_model_only':True,'current_self_HELLO_live_same_UID_tested':True,
 'bootstrap_fixture_executed':True,'native_Terminal_sudo_text_rendered_and_syntax_checked_only':True,
 'observer_timeout':'same helper/kernel incarnation and connection retained; partial frame retained; never auto restart/kill/reset',
 'restart_policy':'user-owned saved JSON/bin cannot recreate live peer authentication; always UNKNOWN_RECORDED_CONTEXT',
 'integrity_scope':'self-image SHA and frame checks are not signatures against a trusted host administrator; fixed root path/kernel UID and actual cross-UID validation still required',
 'prior_evidence_reused_not_rerun':{'stage193_local_checks':58,'stage192_journal':18,'stage191_wire':55},
 'remaining':['independent no-IOKit root-only fake object program and fixed user501/0500/protected path validation plan before separate concrete approval',
 'actual root-to501 identity/path/HELLO/ACK behavior; native frame/bootstrap launch admission remains closed',
 'protected durable result archive and authenticated readback after observer restart',
 'new separate device trial authority; no reuse of consumed05 or unapproved06-10',
 'current same-body p1/guarded launch, backup restore and independent cold-boot rescue; actual target MAIN HD HEVC and long-record acceptance'],
 'goal_complete':False,'persistent_write_release':False})
for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
 if '://' not in link and link!='verification-receipt.json':assert (HERE/link.strip('<>')).resolve().exists(),link
keyfiles=['README.md','build-receipt-v2.json','supervisor-results.json','incremental-stream-result.json','test_supervisor.py','test_incremental_stream.py',
 'supervisor.py','controller_ipc.py','fixed_launch.py','receipt_receiver.py','helper_hello.c','owner_receipt.c','owner_entry_main.c','implementation-review.json','primary-source-review.json','native-goal-observed.json']
put('verification-receipt.json',{'status':'PASS_FIXED_LAUNCH_SELF_HELLO_REVIEW','created_utc':now,'local_checks':17,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),'lowlevel_byte_identical_to193':same,
 'native_helper_released_or_executed':False,'root_or_camera_operations':0,'physical_backup_restore_or_recording_proven':False,
 'files':[{'path':n,'bytes':(HERE/n).stat().st_size,'sha256':digest(HERE/n)} for n in keyfiles]})
new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
new['research_activity']='Integrated exclusive shell launch, actual helper kernel identity, self-image HELLO before ACK, observe/end, private receipt and terminal observation using own unprivileged fake objects.16 full-flow plus1 incremental stream checks pass. Fixed protocol CLOCK_MONOTONIC mismatch. Native10 remains0; root0500 deferred hash is only a policy model, not actual root proof. Restart user files remain UNKNOWN; no administrator/device operation.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('194接通固定假对象启动/实际helper核验/自读HELLO/观察/私有回执；16流程+1分段实流通过。发现并修正Python与C绝对时钟混用；root0500摘要在Root同连接自读后核对，仍只做模型与同UID。重启日志拒绝恢复authenticated；原生10未发布未运行，无root/设备动作，全部16项与授权不变。')
evidence={'readme':REL+'/README.md','build':REL+'/build-receipt-v2.json','verification':REL+'/verification-receipt.json',
 'flows':REL+'/supervisor-results.json','stream':REL+'/incremental-stream-result.json','limitations':REL+'/implementation-review.json',
 'total_local_checks':17,'fixture_launch_and_supervisor_integrated':True,'native_or_root_cross_UID_validated':False,'new_root_or_camera_operations':0}
new['latest_stage_evidence']['stage194_fixed_launch_and_self_HELLO']=evidence
new['current_native_owner_channel_candidate']={**evidence,'identifier':'fx3-702-supervised-owner-20261029-10','explicitly_approved':False,
 'native_authentication_scope_released':False,'bootstrap_supervisor_and_global_fence_ready':False,'authenticated_final_result_delivery_ready':False,
 'self_image_HELLO_and_same_UID_supervision_implemented':True,'root0500_policy_model_only':True,'trusted_restart_receipt_ready':False,
 'same_body_backup_restore_or_independent_rescue_proven':False}
new['next_safe_offline_actions']=[
 '完成独立且不链接IOKit的root仅主机假对象程序/固定bundle和Terminal方案；使用独立host-only编号与日志，不能清除真实设备排他记录。精确约束root0500自读/501观察者/peer/ACK与受保护文件后，才请求该具体单次执行；不操作相机。',
 '补root私有结果归档与重新鉴别的只读查询路线；重启后用户JSON/bin仍不是authenticated证明。原生10实际Frame/启动放行保持关闭，旧05已耗，06-10无新增批准。',
 'Root跨UID验证后再形成新的具体MSC设备方案和独立批准；不由本轮放行Sony认证/文件/p1读取/模块/写入。',
 '保留恢复优先与全部16项：继续当前同机p1获取/受限工作器启动、独立boot/updater选择与WBI/冷启动研究，不因没有修改包停止适配；实际恢复和MAIN HD HEVC录制均待验。'
]
for k in ('authorization','requirements','prepared_first_device_trial','research_priority'):assert new[k]==old[k]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
index=ROOT/'README.md';ib=index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3固定启动监督与程序自读握手](<'+REL+'/README.md>)：16项完整假对象流程＋1项分段实流通过；修正协议时钟混用，relay不充helper，重启日志保持UNKNOWN；原生10关闭，root跨UID和真实恢复未验，无设备动作。'
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
 if stat.S_ISLNK(mode):excluded.append({'path':str(p.relative_to(ROOT)),'link_text':os.readlink(p),'not_followed':True});continue
 if stat.S_ISREG(mode):members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
 elif not stat.S_ISDIR(mode):excluded.append({'path':str(p.relative_to(ROOT)),'mode':oct(mode),'not_opened':True})
put('final-receipt.json',{'schema':'fx3-stage194-fixed-launch-self-HELLO-v1','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),'files':members,'member_count':len(members),
 'excluded':excluded,'mutable_heads_not_manifest_members':True,'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),
 'local_checks':17,'native_candidate_released_or_executed':False,'new_root_or_camera_operations':0,'native_goal_observed':'active',
 'native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(members),'checks':17,
 'native_goal':'active','root_or_camera_operations':0,'goal_complete':False}))
