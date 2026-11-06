"""Recheck offline driver/rate sources and register stage209; no device/guest/root."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
from io import BytesIO
from elftools.elf.elffile import ELFFile
import ast,json,os,plistlib,re,stat,subprocess,tarfile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R));P=B/'stage208-Backup-record-routing'
PREV='f107f7c1c5bc87e3ba84bbf3f49914601693bb513edfe820bcdf4603086b4685';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        while chunk:=f.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,value):
    with (H/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==54
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
binding=json.loads((H/'kernel-source-binding.json').read_text());assert digest(R/binding['source_image'])==binding['source_image_sha256']=='ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568'
assert digest(R/binding['existing_capture'])==binding['kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c' and binding['kernel_bytes']==6610952
selection=json.loads((H/'current-kernel-symbol-selection.json').read_text());assert selection['symbols_recovered']==41269 and selection['reparsed_matches_prior_catalog'] and digest(R/selection['parser_source'])==selection['parser_sha256']
proof=json.loads((H/'GPIO-and-SIO-contract-proof.json').read_text());kc=json.loads((H/'current-GPIO-function-capture.json').read_text());assert len(kc['ranges'])==7
assert proof['GPIO']['GPIO4_physical_base']=='0xf1021000' and proof['GPIO']['param_bytes']==16
assert proof['GPIO']['current_mode9_write_order']==['PORTSEL_SET+0x34','INEN_SET+0x24','WDATA_SET+0x44','DIR_SET+0x04']
assert not proof['GPIO']['reference_explicit_INEN_SET'] and not proof['GPIO']['initial_state_or_transient_pin_levels_proven']
assert proof['SIO']['current7_02_helper_request42_value']==19 and proof['SIO']['reference_payload_rate_index']==3 and not proof['SIO']['same_effective_frequency_proven']
assert not proof['SIO']['current7_02_installed_p1_module_identity_proven']
all_ranges=[]
for row in kc['ranges']:all_ranges.append(dict(row,source=kc['kernel_source'],source_sha256=kc['kernel_sha256'],layout='kernel_file_offset'))
all_ranges.extend(proof['additional_original_ranges']);assert len(all_ranges)==16
for row in all_ranges:
    p=R/row['source'];raw=p.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];a,z=row['start'],row['end_exclusive']
    if row['layout']=='kernel_file_offset':part=raw[a:z]
    else:
        e=ELFFile(BytesIO(raw))
        if row['layout']=='ELF_text_offset':part=e.get_section_by_name('.text').data()[a:z]
        else:
            s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']);at=s['p_offset']+a-s['p_vaddr'];part=raw[at:at+z-a]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
assert len(proof['source_line_pins'])==7
for row in proof['source_line_pins']:
    p=R/row['source'];raw=p.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];part=b''.join(raw.splitlines(keepends=True)[row['start_line']-1:row['end_line_inclusive']]);assert sha256(part).hexdigest()==row['sha256'] and part==(R/row['output']).read_bytes()
layout=next(r for r in proof['source_line_pins'] if r['output'].endswith('/GPL-port-layout.txt'));assert [layout['start_line'],layout['end_line_inclusive']]==[74,83]
refinement=json.loads((H/'source-pin-refinement.json').read_text());assert digest(R/refinement['original_saved'])==refinement['original_pin_sha256']
cap=json.loads((H/'GPIO-source-capture.json').read_text());assert len(cap['files'])==3 and digest(R/cap['archive'])==cap['archive_sha256']=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
with tarfile.open(R/cap['archive'],'r:gz') as tf:
    for row in cap['files']:
        raw=(R/row['output']).read_bytes();assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'] and tf.extractfile(row['member']).read()==raw
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert len(old['requirements'])==16 and native['goal']['status']=='active' and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='CURRENT_GPIO_CONTRACT_AND_SIO_RATE_VALUE_DIFFERENCE_BOUND',previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Current package GPIO ioctl/struct/resource4/mode9 stores now pinned. Current7.02 helper SIO request42=19, reference payload rate3; historic2.05 provider maps request42 to rate registers. Different clock parents may explain values; investigate frequency formula/parents instead of uncritically copying3 or19.',
    limits=proof['limits'],root01='195 specific approval pending; no launch/job or repeated question',Sony_code_or_guest_execution=False,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_OFFLINE_GPIO_DRIVER_AND_RATE_DIFFERENCE_BINDING',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=54,
    kernel_source_image_reverified=True,kernel_bytes=6610952,recovered_symbol_count=41269,original_ranges_reverified=16,source_line_pins_reverified=7,GPL_character_driver_members=3,
    GPIO4_physical='0xf1021000',current_mode9_register_stores=4,reference_explicit_INEN_SET=False,current_helper_rate_request=19,reference_payload_rate=3,
    same_Hz_or_live_gpio_or_transport_proven=False,current_body_p1_identity_proven=False,
    host01_bundle_sha256_unchanged=HOST,host01_job_absent=True,release0_4_zip_unchanged=True,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Bound exact package7.02 GPIO ioctl16B/portid+4/bitnum+8/mode9 store order and GPIO4 resource F1021000; current kernel rebound to p3 and41269symbols reparsed.7.02 helper SIO request19 differs from reference payload3; historical2.05 register interpretation labeled, same Hz/current p1 unproven.16ranges/7source pins, no Sony/guest/root/device actions;195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('209绑当前GPIO ioctl16B/模式9四写与端口4物理资源F1021000；p3原内核重绑/41269符号。当前helper速率请求19与参考3不同，历史p1解释单列，不能直接替换或推Hz。16原范围/7源码行；下一项父时钟/分频，无设备/root/guest，16要求/授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',contract=REL+'/GPIO-and-SIO-contract-proof.json',kernel_binding=REL+'/kernel-source-binding.json',kernel_functions=REL+'/current-GPIO-function-capture.json',GPL_capture=REL+'/GPIO-source-capture.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage209_current_GPIO_and_SIO_rate_difference']=ev
new['recovery_current_GPIO_and_SIO_rate_difference']={**ev,'current_package_GPIO_contract_bound':True,'current_package_GPIO4_resource':'0xf1021000','current_helper_rate_request':19,'reference_payload_rate':3,
    'GPIO_init_order_or_input_enable_equivalent':False,'same_effective_SIO_Hz_proven':False,'actual_current_body_p1_provider_or_transport_proven':False,'same_body_backup_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准、不启动、不重问；主机试验不自动放行相机。',
    '查SIO父时钟/速率计算合同并区分AP Linux与早期SRAM运行环境，解释当前helper19与参考3的字值差异，不未经证明直接替换；核对GPIO输入使能和顺序差异所需初始状态。',
    '保留当前同机p1/ROM与独立AP入口、MCU状态/CRC/回复时效、同机boot0/p1备份、逆写和独立救砖实测；完整16要求及真实MAIN1080p29.97 HEVC长录仍待验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib);marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3当前GPIO驱动与SIO速率差异](<'+REL+'/README.md>)：当前GPIO布局/模式9四写及F1021000资源已绑；helper速率请求19与参考3不同，Hz/当前p1仍未证。16原范围/7源码行，195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage209-current-GPIO-and-SIO-rate-difference-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=54,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),source_ranges=16,source_line_pins=7,current_helper_rate=19,reference_rate=3,same_Hz_proven=False,
    requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
