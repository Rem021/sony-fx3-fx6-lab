"""Source verification and stage211 state registration. No root/device/guest."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,json,os,plistlib,re,stat,struct,subprocess,tarfile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R));P=B/'stage210-SIO-clock-routing-and-divider-contract'
PREV='50332adf883375fede67404a7bea75522c3421f096037ec6d77f1ef0abc2b081';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        while chunk:=f.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,value):
    with (H/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==61
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
proof=json.loads((H/'runtime-and-default-rate-proof.json').read_text());assert len(proof['selected_original_ranges'])==15
for row in proof['selected_original_ranges']:
    raw=(R/row['source']).read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];a,z=int(row['start'],16),int(row['end_exclusive'],16);base=int(row['base'],16);part=raw[a-base:z-base]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
c=proof['C_initialization'];assert c['bytes']==7480 and c['write_unit_bytes']==4 and c['clears_current_SIO_rate_and_channel_CS_fields'] and not c['later_rate_initialization_proven']
v=json.loads((H/'SIO-Backup-property-results.json').read_text());assert len(v['templates'])==11 and len(v['IDs'])==7
for t in v['templates']:
    raw=(R/t['source_path']).read_bytes();assert sha256(raw).hexdigest()==t['source_sha256']
    for rec in t['records']:
        a=rec['offset'];end=a+rec['record_bytes'];assert sum(raw[a:a+32])+sum(raw[a+36:end])==struct.unpack_from('<I',raw,a+32)[0]
        for p in rec['selected_properties']:
            at=p['value_file_offset'];part=raw[at:at+4];assert p['present'] and p['bytes']==4 and sha256(part).hexdigest()==p['raw4_sha256'] and int.from_bytes(part,'little')==p['value_u32']
        assert next(p['value_u32'] for p in rec['selected_properties'] if p['id']=='0x51002c')==3
cross=json.loads((H/'PMCA-rate-crosscheck.json').read_text());assert cross['records']==22 and cross['cases']==154 and len(cross['checks'])==154 and all(x['match'] for x in cross['checks'])
assert cross['buffers_readonly'] and not cross['USB_modules_loaded'] and not cross['source_files_modified']
fmt=json.loads((B/'stage207-Backup-template-and-GPIO-config/format-source-capture.json').read_text());assert fmt['commit']==cross['source_commit']
for row in fmt['files']:assert digest(R/row['output'])==row['sha256']
bk=json.loads((H/'boot-backup-reference-and-list.json').read_text());assert digest(R/bk['reference_source'])==bk['reference_sha256'] and digest(R/bk['current_list'])==bk['current_list_sha256']
raw=(R/bk['reference_source']).read_bytes()[0x8800:0x9000];assert sha256(raw).hexdigest()==bk['block_sha256'] and struct.unpack_from('<II',raw)==(0x42534b42,66)
for i in range(66):
    ident,at,size=struct.unpack_from('<III',raw,8+12*i);assert at>=800 and at+size<=len(raw)
assert next(x['value_u32'] for x in bk['selected'] if x['ID']=='0x51002c')==3 and bk['current_list_count']==65
catalog=proof['current_package_catalog'];assert digest(R/catalog['source'])==catalog['source_sha256'];archive=Path(catalog['NOR_inner_archive']['output']);assert digest(archive)==catalog['NOR_inner_archive']['sha256']
with tarfile.open(archive,'r:') as tf:
    members=[m for m in tf.getmembers() if m.isfile()];assert len(members)==4
    assert tf.extractfile('LdrBkupList.txt').read()==(R/bk['current_list']).read_bytes()
assert not catalog['LdrBkup_bin_members']
profile=json.loads((H/'FX3-early-link-profile-candidate.json').read_text());assert [profile['SIO_rate_word'],profile['SIO_channel'],profile['GPIO_portid'],profile['GPIO_bitnum']]==[3,0,4,2]
for k in ['executable_payload','device_operation_authorized','persistent_write_release','current_body_backup_or_independent_restore_proven','current_NOR_final_rate_load_proven','actual_clock_Hz_or_transport_proven']:assert not profile[k]
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert len(old['requirements'])==16 and native['goal']['status']=='active' and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='PUBLIC_DEFAULT_RATE3_CANDIDATE_AND_INITIAL_ZERO_WRITER_BOUND',previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Classic FX3 rate property0x51002C is3 in all22default records; peer boot BKSB and exact consumer agree. This justifies offline profile3/0/4/2 while Linux firmware writer19 remains distinct. Current C-init clears the rate fields first; later current NOR assignment and actual startup Backup still missing. Next inspect generated LdrBkup/formatter data path and postzero assignment, not confuse initialzero or publicdefault with live value.',
    limits=proof['limits'],root01='195 specific approval pending; no launch/job or repeated question',third_party_host_parser_execution_on_readonly_buffers=True,Sony_code_or_guest_execution=False,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_SOURCE_BOUND_INITIAL_ZERO_AND_DEFAULT_RATE3',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=61,
    original_ranges_reverified=15,classic_templates=11,BK4_records=22,PMCA_independent_property_cases=154,rate_property='0x51002c',all_public_template_rate_values=3,
    reference_BKSB_properties_bounds_checked=66,reference_BKSB_rate=3,current_NOR_list_properties=65,NOR_inner_archive_members=4,
    conditional_C_init_zero_bytes=7480,nonexecutable_candidate_profile=[3,0,4,2],current_NOR_final_rate_load_or_live_Hz_proven=False,
    host01_bundle_sha256_unchanged=HOST,host01_job_absent=True,release0_4_zip_unchanged=True,new_approval_granted=False,third_party_host_parser_execution_on_readonly_buffers=True,Sony_code_or_guest_execution=False,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Bound current C-init region zero7480bytes covering SIO fields and peer rate0x51002C consumer/BKSB3. All22classic default records rate3;154independent PMCA checks agree. Offline profile3/0/4/2 justified, current later assignment/Backup/Hz unresolved.15original ranges; current NOR list65IDs and4member archive bound. No Sony/guest/root/device action;195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('211绑C初始化7480B零写首阶段和参考速率属性51002C消费/BKSB值3；11经典模板22记录均3，154独立PMCA一致。离线候选3/0/4/2已有默认依据，Linux写程序19另列；当前后续赋值/同机BKSB/Hz未验。15原范围，65ID/内层4成员；无设备/root/guest，16要求与授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',proof=REL+'/runtime-and-default-rate-proof.json',default_values=REL+'/SIO-Backup-property-results.json',PMCA=REL+'/PMCA-rate-crosscheck.json',BKSB=REL+'/boot-backup-reference-and-list.json',candidate=REL+'/FX3-early-link-profile-candidate.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage211_runtime_zero_and_default_rate3']=ev
new['recovery_runtime_zero_and_default_rate3']={**ev,'public_rate_ID':'0x51002c','public_classic_default_rate':3,'offline_candidate_rate_channel_port_bit':[3,0,4,2],
    'current_C_init_conditional_zero_bytes':7480,'current_NOR_later_rate_assignment_proven':False,'actual_current_body_Backup_or_SIO_Hz_proven':False,'same_body_backup_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准、不启动、不重问；主机试验不自动放行相机。',
    '核对生成/装入LdrBkup.bin的官方formatter/脚本及其清单、写入范围，明确须保存的同机启动数据；只做现存文件静态分析，不运行formatter/认证/机身接口。',
    '以官方默认速率3/通道0/GPIO4,2为离线候选继续追当前NOR清零后的配置装入、调用者与SIO父时钟，不把参考消费者或默认值充实机值；保留同机boot0/p1、独立AP入口、备份逆写/救砖及16要求和真实MAIN1080p29.97 HEVC长录验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib);marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3运行时初始化与默认速率3](<'+REL+'/README.md>)：22默认记录速率3/154独立例及参考消费已核，离线候选3/0/4/2；C初始化先零7480B，当前后续装入/同机BKSB未证。15原范围；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage211-runtime-zero-and-default-rate3-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=61,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,new_approval_granted=False,
    third_party_host_parser_execution_on_readonly_buffers=True,Sony_code_or_guest_execution=False,root_or_device_operations=0,native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),source_ranges=15,default_rate3_records=22,PMCA_property_cases=154,current_final_rate_load_proven=False,
    requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
