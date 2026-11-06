"""Seal a concrete unapproved host-only root plan; no administrator action."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import json,os,plistlib,re,stat,subprocess
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
PRIOR=BASE/'stage194-supervised-fixed-launch';REL=str(HERE.relative_to(ROOT))
PRIOR_SHA='ae0a501a38b5e8cf6d18ef5455a256ae52823c90ad1fe403d0aac13105f8f9fc'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
 with (HERE/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (HERE/'final-receipt.json').exists()
assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
prior=json.loads((PRIOR/'final-receipt.json').read_text())
for e in prior['files']:
 p=ROOT/e['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
for e in json.loads((HERE/'source-before.json').read_text()):assert digest(ROOT/e['source'])==e['sha256']
b=json.loads((HERE/'build-receipt.json').read_text())
assert not b['root_candidate_executed'] and not b['specific_admin_approval'] and not b['owner_USB_firmware_backends_linked']
for e in b['sources']:assert digest(HERE/e['path'])==e['sha256']
for k,e in b['builds'].items():
 assert digest(Path(e['path']))==e['sha256']
 assert 'IOKit.framework' not in e['dependencies'] and 'libusb' not in e['dependencies']
 assert not any(x in e['undefined_symbols'] for x in ('_IOService','_IORegistry','_IOCreatePlugIn','_IOUSB','_IOConnect','_libusb_','_setauid','_setaudit'))
root_argv=b['builds']['root_host']['argv']
assert not any(any(t in x for t in ('owner_core.c','owner_iokit.c','iokit_wire.c','native_session.c','owner_fixture.c','fake_iokit.c')) for x in root_argv)
tests=json.loads((HERE/'host-test-results.json').read_text());boundary=json.loads((HERE/'approval-boundary-results.json').read_text())
assert tests['tests_run']==15 and tests['status']=='PASS_HOST_ONLY_TRIAL_AND_READBACK' and all(e['status']=='PASS' for e in tests['results'])
assert boundary['tests_run']==2 and boundary['status']=='PASS_EXACT_HOST_APPROVAL_AND_LAYOUT'
assert tests['test_source_sha256']==digest(HERE/'test_host.py') and tests['build_receipt_sha256']==digest(HERE/'build-receipt.json')
for name,h in tests['python_sources'].items():assert digest(HERE/name)==h
assert boundary['test_source_sha256']==digest(HERE/'test_approval_boundary.py')
assert boundary['plan_source_sha256']==digest(HERE/'host_plan.py') and boundary['supervisor_source_sha256']==digest(HERE/'host_supervisor.py')
assert not tests['root_candidate_executed'] and tests['administrator_or_camera_operations']==0
assert not boundary['actual_root_job_created'] and not boundary['actual_root_candidate_executed']
bundle_raw=(HERE/'approval-bundle.json').read_bytes();bundle=json.loads(bundle_raw);bundle_sha=sha256(bundle_raw).hexdigest()
assert bundle_sha=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'==boundary['bundle_sha256']
assert not bundle['admin_execution_approved'] and not bundle['root_candidate_executed'] and bundle['maximum_helper_invocations']==2
for e in bundle['files']:assert (HERE/e['path']).stat().st_size==e['bytes'] and digest(HERE/e['path'])==e['sha256']
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01'),'fixed job unexpectedly exists'
ps=subprocess.check_output(['/bin/ps','-axo','command='],text=True)
assert not any(str(HERE) in s and ('/host-fixture-helper' in s or '/root-host-helper' in s or '/Fixture.command' in s) for s in ps.splitlines()),'host program still live'
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(PRIOR/'goal-status-after.json').read_bytes()
old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
now=datetime.now(timezone.utc).isoformat()
put('primary-source-review.json',{'checked_utc':now,'sources':[
 {'url':'https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html','access':'initial open timeout, later primary search excerpt available','scope':'fsync success is not equated to sudden-power-loss durability; no power-loss claim here'},
 {'url':'https://developer.apple.com/documentation/xcode/reducing-disk-writes','access':'primary search excerpt','scope':'even stronger flushes have limits; no guarantee applied to this fixture or camera'},
 {'url':'https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/uipc_usrreq.c','access':'earlier193 live primary check reused; not redownloaded this turn','scope':'kernel Unix peer identity/disconnection boundary only'}],
 'camera_or_root_operations':0,'source_evidence_does_not_release_device_actions':True})
put('implementation-review.json',{'status':'HOST_ONLY_ROOT_TRIAL_AND_READBACK_CONCRETE_UNAPPROVED',
 'host_grant_id':bundle['grant_id'],'approval_bundle_sha256':bundle_sha,'root_helper_sha256':b['builds']['root_host']['sha256'],
 'local_checks':17,'host_flow_checks':15,'approval_layout_checks':2,'root_candidate_executed':False,'root_or_device_operations':0,
 'no_IOKit_USB_owner_firmware_backend_linked':True,'maximum_helper_invocations_if_approved':2,
 'scope':'self/process/login metadata, fixed private files, AF_UNIX and64B RAM checksum only; separate host-only journal',
 'actual_root_cross_UID_or_root_protected_files_validated':False,
 'persistence_limit':'current checksum-validated archive/readback; fsync does not prove sudden-power-loss durability or camera recovery',
 'context_loss_test':'first-stage live proof cleared in same unprivileged observer process; not actual Orca restart',
 'approval_limit':'new exact bundle +HOST_ONLY+2invocations required before staging/open/sudo; old grants denied; no automatic retries or device grant',
 'device_candidate10_unchanged_and_closed':True,
 'remaining':['user-specific single host-only root approval and actual cross-UID/self-image/protected readback receipt',
 'new independent camera trial scope and final source/bundle release; consumed05 and unapproved06-10 cannot substitute',
 'same-body currentp1, constrained launch, real backup restore/independent recovery and target MAIN HD HEVC recording'],
 'goal_complete':False,'persistent_write_release':False})
for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
 if '://' not in link:assert (HERE/link.strip('<>')).resolve().exists(),link
keyfiles=['README.md','approval-bundle.json','fixed-plan.json','build-receipt.json','host-test-results.json','approval-boundary-results.json',
 'host_trial.c','host_supervisor.py','host_records.py','host_plan.py','run_approved_host.py','implementation-review.json','primary-source-review.json','native-goal-observed.json']
put('verification-receipt.json',{'status':'PASS_HOST_ONLY_ROOT_PLAN_REVIEW','created_utc':now,'local_checks':17,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'approval_bundle_sha256':bundle_sha,'root_candidate_executed':False,'administrator_or_camera_operations':0,
 'files':[{'path':n,'bytes':(HERE/n).stat().st_size,'sha256':digest(HERE/n)} for n in keyfiles]})
new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
new['research_activity']='Built separate host-only root candidate without owner/IOKit/USB/firmware backend;15 unprivileged executable flow checks plus2 nonexecuting approval/layout checks pass. Fixed plan includes one sudo chain with maximum2 helper invocations:64B RAM trial/private archive, then fresh-nonce readback. Specific approval not granted, root candidate and fixed job never started. Camera candidate10 remains unchanged/closed; full16requirements unchanged.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('195完成独立root仅主机01程序与精确bundle；15普通用户进程/归档/回读测试+2批准边界/模板映射检查通过。root版本、固定/private/tmp作业和管理员请求均未启动。Root仅两次固定helper、独立HOST日志，既有10设备候选仍关闭；17检查不充相机备份/恢复/主录，16要求及全部授权保持。')
evidence={'readme':REL+'/README.md','build':REL+'/build-receipt.json','verification':REL+'/verification-receipt.json',
 'flows':REL+'/host-test-results.json','approval_boundary':REL+'/approval-boundary-results.json','bundle':REL+'/approval-bundle.json',
 'total_local_checks':17,'root_candidate_executed':False,'administrator_or_camera_operations':0}
new['latest_stage_evidence']['stage195_root_host_validation_plan']=evidence
new['prepared_root_host_trial']={**evidence,'grant_id':bundle['grant_id'],'bundle_sha256':bundle_sha,
 'scope':'HOST_ONLY','maximum_helper_invocations':2,'explicitly_authorized':False,'released_for_execution':False,
 'user_job_or_root_artifact_staged':False,'camera_operations_released':False,'status':'prepared_waiting_new_specific_approval'}
new['next_safe_offline_actions']=[
 '先向用户请求195固定bundle的新单次HOST_ONLY批准：一次Terminal/sudo，最多trial/readback各1次；仅主机64B RAM、自身身份、私有文件及nonce回读，无IOKit/USB/驱动/相机/权限调整。批准前不创建固定作业、不打开Terminal、不执行root。',
 '若获该精确批准，在新执行阶段记录授权并重验195bundle/Root程序hash，运行固定监督器，用户自行完成必要原生验证；观察实际root与501、0500自读、受保护回执，任何阻塞/失败保持UNKNOWN不重试。该批准不能给10设备候选或任何相机动作。',
 '等待期间可继续仅离线恢复优先研究：同机当前p1入口、受限工作器、独立boot/updater/WBI冷启动，不以缺修改包阻断适配；16目标及实际恢复/MAIN HD HEVC验收仍保留。'
]
for k in ('authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate'):assert new[k]==old[k]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
index=ROOT/'README.md';ib=index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3研究root仅主机01固定方案](<'+REL+'/README.md>)：独立无IOKit/USB/固件后端程序；15项普通用户流程＋2项批准/映射检查通过，试验＋新nonce回读最多两次helper，待新的具体批准，root/作业/管理员/相机均未运行。'
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
put('final-receipt.json',{'schema':'fx3-stage195-root-host-validation-plan-v1','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'files':members,'member_count':len(members),'excluded':excluded,'mutable_heads_not_manifest_members':True,
 'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),
 'local_checks':17,'approval_bundle_sha256':bundle_sha,'root_candidate_executed':False,'new_root_or_device_operations':0,
 'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(members),'checks':17,
 'approval_bundle_sha256':bundle_sha,'root_candidate_executed':False,'specific_approval':False,'native_goal':'active'}))
