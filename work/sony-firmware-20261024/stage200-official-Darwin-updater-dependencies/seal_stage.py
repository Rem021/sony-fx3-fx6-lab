"""Register source-bound official sender/dependency findings; preserve device gates."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
P=B/'stage199-Darwin-vector-map-and-update-entry';REL=str(H.relative_to(R))
PSHA='6b4b00a24be1331e852f38ef6fe7be0289c27f3dc3587a185f673bb38dcad5d5'
HSHA='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists()
assert digest(P/'final-receipt.json')==PSHA
prior=json.loads((P/'final-receipt.json').read_text())
for e in prior['files']:
    p=R/e['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
assert len(prior['files'])==40
cap=json.loads((H/'source-capture.json').read_text());providers=json.loads((H/'provider-capture.json').read_text())
proof=json.loads((H/'official-sender-proof.json').read_text());entry=json.loads((H/'entry-and-dependency-audit.json').read_text())
for e in cap['sources']:
    p=Path(e['path']);assert p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
for e in cap['captures']+providers['providers']:
    p=Path(e['output']);assert p.stat().st_size==e['bytes'] and digest(p)==e['sha256']
for e in cap['parser_sources']:assert digest(Path(e['path']))==e['sha256']
assert digest(Path(providers['GPL_reference']['path']))==providers['GPL_reference']['sha256']
assert digest(Path(providers['current_main_AP_image']))==providers['current_main_AP_image_sha256']
assert proof['official_sender']['first_bytes']==[17,4] and proof['official_sender']['frame_bytes']==128
assert proof['reference_SIO_contract']['argument_copy_bytes']==32 and proof['reference_SIO_contract']['selected_copy_success_return']==128
assert proof['historical_module_identity']['different_bytes_only_within_build_id_note']
assert proof['historical_init_result_limit']['target_state4_not_implied_by_exit0']
assert proof['MCU_CRC_limit']['peripheral_base']=='0x40039000' and not proof['MCU_CRC_limit']['hardware_result_equivalence_to_AP_software_CRC_verified']
assert len(proof['selected_original_ranges'])==14 and len(entry['helper_startup_bindings'])==2

# Check every selected source range against the original source mapping.
from io import BytesIO
from elftools.elf.elffile import ELFFile
for e in proof['selected_original_ranges']:
    p=Path(e['source']);raw=p.read_bytes();assert sha256(raw).hexdigest()==e['source_sha256']
    a,z=int(e['start'],16),int(e['end_exclusive'],16)
    if e['address_kind']=='source_layout_VA':part=raw[a-0x4200:z-0x4200]
    else:
        elf=ELFFile(BytesIO(raw))
        if e['address_kind']=='text_section_offset':part=elf.get_section_by_name('.text').data()[a:z]
        else:
            matches=[s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']]
            assert len(matches)==1;s=matches[0];off=s['p_offset']+a-s['p_vaddr'];part=raw[off:off+z-a]
    assert len(part)==e['bytes'] and sha256(part).hexdigest()==e['sha256']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HSHA
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
release=R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip'
assert digest(release)=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link:assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert canonical.read_bytes()==before==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert native['goal']['status']=='active' and len(old['requirements'])==16
assert not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('analysis-corrections.json',{'scope':'host-only unsealed analysis; no device/guest retries',
 'corrections':['used actual SquashFS class after initial incorrect class-name import, before any source capture',
  'rejected whole.text as complete code when literal-pool words stopped sequential decoding; all4B output now locator-only, selected14 code ranges separately checked',
  'used existing project venv after plain Python lacked pyelftools; no dependency installation'],
 'Sony_or_guest_execution':False,'root_or_device_operations':0})
put('implementation-review.json',{
 'status':'OFFICIAL_7_02_DARWIN_AP_SENDER_LOCATED_NOT_AP_BOOTSTRAP',
 'new_facts':['current7.02 Ubody ELF constructor writes0x11/4 in128B frame and calls camera SIO/GPIO; entry main bound from original_start literal',
  'reference P1 SIO recognizes request0x40046740 with32B args; selected128B success path returns128, not0',
  '2.04/2.05 reference init helper identical; SIO modules differ only GNU build-id bytes, not current-body attestation',
  'historical helper can return0 on selected expired-timer path without target state4; ordinary init wrapper ignores result and exits0',
  'MCU CRC routine uses register peripheral0x40039000, no guessed hardware emulation used'],
 'limits':['source field match and selected driver paths only; no physical transport/MCU CRC equivalence/current p1 identity',
  'official route assumes running camera Linux environment, libraries, SIO/GPIO and Backup configuration; does not bootstrap dead AP',
  'historical wrapper/driver observations are not a current-body error diagnosis',
  'same-body p1/boot0, independent inverse write and MAIN HD HEVC recording/long-record acceptance remain unverified'],
 'scope_counts':{'captured_locator_original_files':len(cap['captures'])+len(providers['providers']),'selected_code_slices':14,'original_or_guest_executions':0,'root_or_device_operations':0},
 'pending_root01':'same195 bundle, no specific response, job absent, no launch or repeated question',
 'goal_complete':False,'persistent_write_release':False})
put('verification-receipt.json',{'status':'PASS_SOURCE_BOUND_OFFICIAL_DARWIN_SENDER_REVIEW','created_utc':now,
 'previous_manifest_sha256':PSHA,'previous_members_reverified':40,'selected_original_slices':14,'entry_main_bindings':2,
 'official7_02_sender_fields':[17,4],'reference_ioctl_argument_bytes':32,'selected_reference_ioctl_return':128,
 'host01_bundle_sha256_unchanged':HSHA,'release0_4_zip_unchanged':True,'new_approval_granted':False,
 'original_or_guest_executions':0,'root_or_device_operations':0,'AP_independent_restore_proven':False})
new=deepcopy(old);new['updated_utc']=now;new['latest_stage']=H.name
new['research_activity']='Official7.02 Ubody AP sender of Darwin Cmd11/sub4 located with startup/main literal binding.128B frame/32B SIO request matches historical P1 driver selected path, whose success return128 differs from helper/script status. Historical init0 cannot alone certify state4; MCU CRC uses peripheral, not a guessed model. Darwin update requires existing AP Linux environment, not independent AP bootstrap.14selected slices, no original/guest/root/device execution;195 still pending.'
new['goal_manager_status']=new['goal_manager_status_last_observed']='active';new['native_goal_state_not_modified']=True
new['current_native_goal_observation']={'receipt':REL+'/native-goal-observed.json','observed_utc':native['observed_utc'],'status':'active','source':'native get_goal read only','device_authorization_expanded':False}
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('200定位当前7.02官方AP发送者：ELF主入口/构帧11/4/128B及SIO参数已核，参考p1驱动32B/成功128；2.04/2.05模块仅buildid差。原初始化0/脚本OK不足证状态4，MCU CRC是外设。14源切片，无guest/root/设备；Darwin更新不再充AP自举候选，转回AP p1/p3和原机来源。195待答，16要求/授权不变。')
evidence={'readme':REL+'/README.md','verification':REL+'/verification-receipt.json','sender':REL+'/official-sender-proof.json','entry_dependencies':REL+'/entry-and-dependency-audit.json','capture':REL+'/source-capture.json','providers':REL+'/provider-capture.json','scope':REL+'/implementation-review.json','web_review':REL+'/web-source-review.json','original_or_guest_execution':False,'root_or_device_operations':0}
new['latest_stage_evidence']['stage200_official_Darwin_sender_and_dependencies']=evidence
new['recovery_Darwin_official_AP_sender']={**evidence,'official7_02_logical_frame_sender_located':True,'historical_reference_driver_shape_matches':True,'physical_delivery_proven':False,'current_p1_identity_verified':False,'AP_updater_bootstrap_proven':False,'independent_restore_proven':False}
new['next_safe_offline_actions']=[
 '195 root01具体问题仍待用户回答；保持原bundle与未授权/作业未创建状态，不把继续或目标续行为批准、不启动管理员、不重复询问。',
 'Darwin Cmd11/sub4的当前官方AP程序发送者已找到，200补齐字段/依赖；不能再作为未定位的泛查项，也不再将依赖AP Linux的Darwin自身更新充独立AP自举方案。',
 '返回AP早期装载、p1/p3选择与可取得的原机启动来源；复用182/183已有队列边界而不重复泛扫。保持当前p1/boot0、真实逆写/独立冷恢复及MAIN HD HEVC等16项要求；任何设备读取/模式操作仍需具体授权。']
for k in ('authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial'):assert new[k]==old[k],k
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
with (H/'goal-status-after.json').open('xb') as f:f.write(after)
index=R/'README.md';ib=index.read_bytes()
with (H/'readme-rebased-before.md').open('xb') as f:f.write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3官方Darwin发送端与驱动依赖](<'+REL+'/README.md>)：7.02原程序11/4构帧和参考p1 SIO32B/128返回已核，脚本OK不充状态确认；依赖AP运行环境，非独立自举；14原切片，195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
with (H/'readme-after.md').open('xb') as f:f.write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name in ((canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')):
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',{'schema':'fx3-stage200-official-sender-v1','created_utc':now,'previous_manifest_sha256':PSHA,'previous_members_reverified':40,'files':members,'member_count':len(members),'mutable_heads_not_manifest_members':True,'goal_before_sha256':sha256(before).hexdigest(),'goal_after_sha256':sha256(after).hexdigest(),'host01_bundle_sha256_unchanged':HSHA,'new_approval_granted':False,'original_or_guest_execution':False,'root_or_device_operations':0,'native_goal_observed':'active','native_goal_status_changed_by_assistant':False,'goal_complete':False,'persistent_write_release':False})
print(json.dumps({'sealed_manifest_sha256':digest(H/'final-receipt.json'),'members':len(members),'requirements_unchanged':16,'all_authorizations_unchanged':True,'root_or_device_operations':0,'goal_complete':False}))
