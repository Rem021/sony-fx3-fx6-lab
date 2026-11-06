"""Rebind local template/provider evidence and register stage207 without device I/O."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
from io import BytesIO
from elftools.elf.elffile import ELFFile
import ast,json,os,plistlib,re,stat,struct,subprocess,tarfile,zlib
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];P=B/'stage206-FX3-MCU-read-protocol';REL=str(H.relative_to(R))
PREV='910577ba157b0d4b15c3145543061eb3a2a6618fd51a4a170cb86b8700e1d4ad'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        while chunk:=f.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()
def put(name,value):
    with (H/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def volume():
    assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==47
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
cap=json.loads((H/'template-source-capture.json').read_text());src=Path(cap['source'])
assert src==B/'fx3-7.02-decrypted.fdat' and digest(src)==cap['source_sha256']=='694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
catalog=json.loads((P/'Backup-template-candidates.json').read_text());known={r['name']:r for r in catalog['members']}
values=json.loads((H/'template-field-results.json').read_text());assert len(cap['files'])==len(values['templates'])==11
# Execute only the own host parser function, without its output-writing top level.
tree=ast.parse((H/'read_template_fields.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='read_record')
ns=dict(struct=struct,sha256=sha256,TARGETS=[0xf900d4,0xf900b1,0xf9006d]);exec(compile(ast.Module(body=[fn],type_ignores=[]),'<own-read-record-check>','exec'),ns)
entry_count=0
with src.open('rb') as f:
    for row,t in zip(cap['files'],values['templates']):
        assert '/ALCIN/' in row['name'] and {k:row[k] for k in known[row['name']]}==known[row['name']]
        raw=(R/row['output']).read_bytes();f.seek(row['fdat_data_offset']);assert f.read(row['size'])==raw
        assert sha256(raw).hexdigest()==row['sha256']==t['source_sha256']
        assert f'{zlib.crc32(raw)&0xffffffff:08x}'==row['crc32']
        assert len(t['records'])==2
        for n,record in enumerate(t['records']):
            parsed,end=ns['read_record'](raw,record['offset']);assert parsed==record
            assert [r['value_u32'] for r in parsed['selected_properties']]==([0,4,2] if n==0 else [5,4,30])
            entry_count+=parsed['property_entries']
        assert end==len(raw) and t['inter_record_padding_bytes']==2260
assert entry_count==735515 and values['selected_source_record'] is None and not values['source_record_role_or_runtime_selection_proven']
assert values['all_first_record_values']==[0,4,2] and values['all_second_record_values']==[5,4,30]
fmt=json.loads((H/'format-source-capture.json').read_text())
assert fmt['commit']=='a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0' and len(fmt['files'])==3
for row in fmt['files']:
    p=R/row['output'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
assert fmt['host_parser_executed_later_readonly'] and not fmt['Sony_code_or_guest_execution']
cross=json.loads((H/'PMCA-reader-crosscheck.json').read_text())
assert cross['records_checked']==22 and cross['property_cases']==cross['present_property_cases']==66 and cross['all_match']
assert cross['buffers_read_only'] and not cross['USB_runtime_modules_loaded'] and not cross['source_files_mutated']
assert len(cross['checks'])==66 and all(r['present'] and r['match'] for r in cross['checks'])
proof=json.loads((H/'GPIO-layout-proof.json').read_text());assert len(proof['selected_ranges'])==7
for row in proof['selected_ranges']:
    raw=(R/row['source']).read_bytes();assert sha256(raw).hexdigest()==row['source_sha256']
    e=ELFFile(BytesIO(raw));a,z=int(row['start'],16),int(row['end_exclusive'],16)
    seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a<z<=s['p_vaddr']+s['p_filesz']);at=seg['p_offset']+a-seg['p_vaddr']
    part=raw[at:at+z-a];assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
current=(R/proof['current_main_provider']).read_bytes();ce=ELFFile(BytesIO(current));comment=ce.get_section_by_name('.comment')
assert proof['main_provider_reverified_against_image'] and proof['ioctl']=='0xc0104702'
for row in proof['historical_provider_comparisons']:
    raw=(R/row['source']).read_bytes();oe=ELFFile(BytesIO(raw));assert sha256(raw).hexdigest()==row['sha256'] and len(raw)==len(current)
    differences=[i for i,(a,b) in enumerate(zip(raw,current)) if a!=b];assert len(differences)==row['differing_bytes']==7
    assert all(comment['sh_offset']<=i<comment['sh_offset']+comment['sh_size'] for i in differences)
    assert all(not any(s['p_offset']<=i<s['p_offset']+s['p_filesz'] for s in ce.iter_segments() if s['p_type']=='PT_LOAD') for i in differences)
    for name in ['.text','.rodata']:assert ce.get_section_by_name(name).data()==oe.get_section_by_name(name).data()
assert not proof['record0_or_record1_mapping_to_actual_AP_read_proven'] and not proof['actual_pin_or_voltage_measured']
gpl=json.loads((H/'GPL-GPIO-source-capture.json').read_text());archive=Path(gpl['archive']);assert digest(archive)==gpl['archive_sha256']
with tarfile.open(archive,'r:gz') as tf:
    for row in gpl['files']:
        raw=(R/row['output']).read_bytes();assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256']
        assert tf.extractfile(row['member']).read()==raw
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert native['goal']['status']=='active' and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='CLASSIC_DEFAULT_RECORDS_AND_NAMED_GPIO_LAYOUT_BOUND_WITH_SELECTION_UNRESOLVED',
    previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Two valid BK4 records differ:0/4/2 versus5/4/30. GPIO inputs named portid/bitnum; mode2 is named OUTPUT_H. Need actual Backup service/record routing before selecting a FX3 profile; matching A7IV defaults alone is insufficient.',
    limits=proof['limits']+['Public defaults are not same-body Backup data','No current-body record role, active pin configuration, target driver or voltage was measured','Current7.02 p1/AP early entry and independent restore remain unproven'],
    root01='195 specific approval pending; no admin launch/job or repeated question',
    third_party_host_parser_modules_executed=['pmca.backup','pmca.util'],Sony_code_or_guest_execution=False,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_OFFLINE_DEFAULTS_AND_GPIO_LAYOUT_BINDING',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=47,classic_templates_rebound_to_FDAT=11,BK4_records_reparsed=22,
    property_entries_current_data_bounds_rechecked=entry_count,PMCA_independent_property_cases=66,
    selected_record0_values=[0,4,2],selected_record1_values=[5,4,30],runtime_record_selection_proven=False,
    original_ELF_ranges_reverified=7,GPIO_arguments_named=True,GPIO_mode2_named_OUTPUT_H=True,historical_GPIO_text_and_rodata_match_versions=['2.04','2.05'],
    host01_bundle_sha256_unchanged=HOST,host01_job_absent=True,release0_4_zip_unchanged=True,new_approval_granted=False,
    third_party_host_parser_execution_on_readonly_buffers=True,Sony_code_or_guest_execution=False,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Decoded11classic ALCIN default templates:22valid BK4 records,735515current-property bounds,66independent PMCA cases. Record0inputs0/4/2 versus record1inputs5/4/30; actual service record selection not proven. Main GPIO provider binds portid/bitnum and mode2 OUTPUT_H,7original ranges; historic text/rodata agree. No Sony/guest/root/device action.195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('207解11经典模板/22有效记录：735515当前属性范围、66独立PMCA例一致；两记录0/4/2与5/4/30不同，不能先选记录0。GPIO portid/bitnum及mode2 OUTPUT_H已绑，7原范围；下一项Backup实际接收及记录选择，无设备/root/guest，16要求与授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',templates=REL+'/template-field-results.json',template_capture=REL+'/template-source-capture.json',
    independent_PMCA_crosscheck=REL+'/PMCA-reader-crosscheck.json',GPIO=REL+'/GPIO-layout-proof.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage207_Backup_defaults_and_GPIO_layout']=ev
new['recovery_Backup_template_and_GPIO_configuration']={**ev,'classic_templates':11,'valid_BK4_records':22,'record0_default_SIO_port_bit':[0,4,2],'record1_default_SIO_port_bit':[5,4,30],
    'GPIO_argument_names_bound':['portid','bitnum'],'mode2_named_OUTPUT_H':True,'selected_runtime_record':None,'actual_current_body_Backup_or_pin_configuration_proven':False,'same_body_backup_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准、不启动、不重问；主机试验不自动放行相机。',
    '沿Backup_read_4Byte请求0x003E014D追实际接收者、文件/记录索引及ordinary/interchip路由；核对为何11份经典模板内两有效记录分别为0/4/2和5/4/30，不因匹配A7IV就选记录0；默认模板仍非实机Backup。',
    '保留GPIO当前驱动/实际电平、InitCom状态/CRC外设/重复回复时效、ROM与启动桥、同机boot0/p1、备份逆写/独立恢复及16要求；真实MAIN1080p29.97 HEVC长录仍待验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n';entry='- [2026-10-29 FX3默认Backup双记录与GPIO参数](<'+REL+'/README.md>)：11模板/22有效记录的两组配置不同，735515范围/66独立例通过；GPIO端口/位号和模式2已绑，7原范围。实际记录选择与救砖未验；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected
    p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage207-Backup-defaults-and-GPIO-layout-v1',created_utc=now,previous_manifest_sha256=PREV,
    previous_members_reverified=47,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,
    new_approval_granted=False,third_party_host_parser_execution_on_readonly_buffers=True,Sony_code_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),BK4_records=22,PMCA_property_cases=66,source_ranges=7,
    runtime_record_selection_proven=False,requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
