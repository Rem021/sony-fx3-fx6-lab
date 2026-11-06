"""Seal source-bound static recovery findings; preserve pending host consent."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
from copy import deepcopy
import json,os,plistlib,re,stat
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE.parents[1]
PRIOR=BASE/'stage195-root-host-validation-plan';REL=str(HERE.relative_to(ROOT))
PRIOR_SHA='a470b2cc945ac7cd83bf5876ef062e028f92cc51ad47dfff6d86c963938ef147'
SOURCE=BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
SOURCE_SHA='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
 with (HERE/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
 import subprocess
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (HERE/'final-receipt.json').exists()
assert digest(PRIOR/'final-receipt.json')==PRIOR_SHA
prior=json.loads((PRIOR/'final-receipt.json').read_text())
for e in prior['files']:
 p=ROOT/e['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
assert digest(SOURCE)==SOURCE_SHA
proof=json.loads((HERE/'fat-open-normal-return-proof.json').read_text());selected=json.loads((HERE/'selected-source-evidence.json').read_text())
assert proof['sha256']==selected['sha256']==SOURCE_SHA
assert proof['instructions']==118 and proof['normal_return_signed32']==selected['normal_return_signed32_from_raw_MOVN']==-408
assert proof['normal_returns']==['0xfe058174'] and proof['dominating_return_setter']=='0xfe05816c'
assert selected['independent_branch_graph_matches'] and selected['source_unchanged_after']
data=SOURCE.read_bytes()
for e in selected['selected_original_ranges']:
 a=int(e['start'],16)-0xfe049000;z=int(e['end_exclusive'],16)-0xfe049000
 assert sha256(data[a:z]).hexdigest()==e['sha256'] and z-a==e['bytes']
assert len(selected['selected_original_ranges'])==10
bundle_sha=digest(PRIOR/'approval-bundle.json');assert bundle_sha=='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
canonical=BASE/'GOAL_STATUS.json';before=(HERE/'goal-status-before.json').read_bytes()
assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
old=json.loads(before);assert len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
native=json.loads((HERE/'native-goal-observed.json').read_text());assert native['goal']['status']=='active'
now=datetime.now(timezone.utc).isoformat()
put('source-review.json',{'checked_utc':now,'official_source_url':'https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561',
 'web_observation':'official7.02 page opened live; failure subsection describes copy/prerequisite-version errors and standard retry; no custom-payload or independent p1 recovery promise inferred',
 'NOR_source':str(SOURCE),'NOR_sha256':SOURCE_SHA,'prior183_evidence_reused_for_locator_only':True,
 'source_unchanged':True,'original_or_guest_execution':False,'camera_USB_admin_Windows_UU_GUI_operations':0,
 'fresh_Sony_package_download_or_install':False})
put('implementation-review.json',{'status':'STATIC_RECOVERY_ROUTE_REFINED_NOT_DEVICE_PROVEN',
 'new_facts':['exact original FAT-open normal-return CFG118instructions returns-408; independent A64 raw branch/MOVN encoding agrees',
 'one exact writer of shared word0xfe170028 is result-bit from UPDATE_MIRA labeled early hardware-register leaf'],
 'GPIO_leaf':'writes masks at0xf102e008/0xf102e024 before sampling0xf102e010 bit1; NOT executed here',
 'scope_limits':['normal ABI returns from calls assumed; no claim callees always return or code is never replaced at runtime',
 'linear address references are candidates and not a complete alias/initialization proof',
 'hardware register address is not a board pad/button mapping or test instruction',
 'COMMON ordering applies only if that path reaches enabled table entries; not every WBI/hot/cold route proven',
 'predicate/SPI field4or7 is not mapped to loader mode3/p1/p3 or Fastboot; remote selection still missing'],
 'next_static_target':'complete0xfe054c88 SPI state consumer and first SPI input/bootdata import, preserving distinct integer domains',
 'pending_host01':'195 bundle unchanged; no new reply/approval, no fixed job or administrator request; question not resent',
 'goal_complete':False,'persistent_write_release':False})
for link in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
 if '://' not in link:assert (HERE/link.strip('<>')).resolve().exists(),link
files=['README.md','analyze_boot.py','prove_fat_cfg.py','word_refs.py','verify_and_capture.py','fat-open-normal-return-proof.json',
 'fat-open-cfg.json','selected-source-evidence.json','source-review.json','implementation-review.json','native-goal-observed.json']
put('verification-receipt.json',{'status':'PASS_SOURCE_BOUND_STATIC_RECOVERY_REVIEW','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'NOR_sha256':SOURCE_SHA,'FAT_open_instructions':118,'normal_return_signed32':-408,'independent_raw_CFG_matches':True,
 'selected_original_slices':10,'new_runtime_tests_or_guest_executions':0,'root_or_device_operations':0,
 'host01_bundle_sha256_unchanged':bundle_sha,'new_approval_granted':False,
 'files':[{'path':n,'bytes':(HERE/n).stat().st_size,'sha256':digest(HERE/n)} for n in files]})
new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
new['research_activity']='Static recovery progress while host01 consent remains pending. Exact7.02 NOR FAT-open118instruction CFG has only normal return-408, verified by independent raw A64 branch/MOVN decoder. Shared updater predicate word producer traced to UPDATE_MIRA register sample bit1, not proven physical button/jig. Do not promote mode filename to independent rescue. No original/guest/device/admin execution; source and195bundle unchanged.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('196在195批准待答时独立推进恢复：原NOR FAT-open118指令正常返回恒-408，独立位编码图复核一致；word0xfe170028已找到UPDATE_MIRA寄存器bit1生产者及COMMON项。文件fallback不再充独立恢复，GPIO/4或7/loader3/p1仍分域。仅宿主静态，10原切片，无Sony/guest/设备/root动作；195bundle与17检查不重跑，16要求/全部授权保持。')
evidence={'readme':REL+'/README.md','verification':REL+'/verification-receipt.json','FAT_CFG':REL+'/fat-open-normal-return-proof.json',
 'selected_original':REL+'/selected-source-evidence.json','limitations':REL+'/implementation-review.json',
 'original_or_guest_code_executed':False,'root_or_device_operations':0}
new['latest_stage_evidence']['stage196_NOR_FAT_and_mode_producer']=evidence
new['recovery_NOR_route_refinement']={**evidence,'FAT_normal_success_return_present':False,
 'ordinary_return_scope_only':True,'shared_word_producer_located':True,'board_trigger_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
 '195 root01精确问题仍待用户回答；保持原bundle和未授权状态，不重复询问、不把继续视为批准、不创建固定作业或启动管理员。若明确批准才进入新的执行阶段，仅HOST_ONLY范围。',
 '继续原NOR完整SPI状态消费者0xfe054c88、首轮输入和bootdata导入；确定远端mode/p1/p3选择。196已证明该原FAT-open普通返回恒-408，不能再以mode字符串/成功分支形状当已可用文件恢复。',
 '把UPDATE_MIRA内部寄存器bit候选与用户按键/实际pad/电平/硬件夹具分开；没有映射和退出合同前不做板级操作，也不将其叫Fastboot。当前p1、备份逆写和MAIN HD HEVC实录等全部16项目标仍保留。'
]
for k in ('authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial'):assert new[k]==old[k]
assert not new['goal_complete'] and not new['persistent_write_release']
encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
index=ROOT/'README.md';ib=index.read_bytes()
with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3 NOR文件回退与早期标志](<'+REL+'/README.md>)：原FAT-open118指令正常返回恒-408，原始位编码复核一致；UPDATE_MIRA采样写word已定位，真实按键/远端p1仍未证；195批准待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (HERE/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'CAS concurrent change'
for dest,data,name in ((canonical,encoded,'.goal.tmp'),(index,ia,'.index.tmp')):
 p=HERE/name
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(p,dest)
members=[]
for p in sorted(HERE.rglob('*')):
 if p.is_file() and not p.is_symlink():members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
put('final-receipt.json',{'schema':'fx3-stage196-early-FAT-boot-selection-v1','created_utc':now,
 'previous_manifest_sha256':PRIOR_SHA,'previous_manifest_members_reverified':len(prior['files']),
 'files':members,'member_count':len(members),'mutable_heads_not_manifest_members':True,
 'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(encoded).hexdigest(),
 'host01_bundle_sha256_unchanged':bundle_sha,'new_approval_granted':False,'root_or_device_operations':0,
 'original_or_guest_execution':False,'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,
 'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'manifest_sha256':digest(HERE/'final-receipt.json'),'members':len(members),
 'FAT_normal_return':-408,'new_hardware_trigger_proven':False,'root_or_device_operations':0,'native_goal':'active'}))
