"""Source recheck and stage208 state registration; no target or administrator access."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
from io import BytesIO
from elftools.elf.elffile import ELFFile
import ast,importlib.util,json,os,plistlib,re,stat,subprocess
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R));P=B/'stage207-Backup-template-and-GPIO-config'
PREV='17474836c1e549ab6f5a6706b3ef9a3a00ea7872d29238e09afa3fffd19566ba';HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        while chunk:=f.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()
def volume():assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,value):
    with (H/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==49
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
cap=json.loads((H/'source-capture.json').read_text());assert len(cap['files'])==5
reader=B/'stage2/extraction/read_filesystems.py';assert digest(reader)=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec=importlib.util.spec_from_file_location('stage208checkfs',reader);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);fs=m.Ext2(R/cap['source_image'])
try:
    assert sha256(fs.b).hexdigest()==cap['source_image_sha256']=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
    chosen={row['image_path']:row for row in cap['files']};found=set()
    for row in fs.walk():
        if row['path'] not in chosen:continue
        c=chosen[row['path']];raw=(R/c['output']).read_bytes();assert len(raw)==c['bytes'] and sha256(raw).hexdigest()==c['sha256'] and fs.data(row['inode'])==raw
        assert row['inode']==c['inode'];found.add(row['path'])
    assert found==set(chosen)
finally:fs.b.close();fs.f.close()
proof=json.loads((H/'record-routing-proof.json').read_text());assert proof['operation_selector']==4 and proof['operation_selector_is_not_length'] and proof['argument_count']==1
assert proof['dispatch_table']['destination']=='0x7f58' and proof['dispatch_table']['signed_halfword']==271
assert proof['classic_public_AP_defaults']==dict(SIO=0,GPIO_portid=4,GPIO_bitnum=2) and proof['classic_public_CP_defaults']==dict(SIO=5,GPIO_portid=4,GPIO_bitnum=30)
assert len(proof['template_layout_checks'])==11 and all(r['local_record_offset']==0 and r['CP_record_offset']==0xd2000 for r in proof['template_layout_checks'])
assert not proof['actual_body_Backup_read'] and not proof['actual_AP_current_settings_or_recovery_execution_proven']
all_ranges=[]
for name in ['function-cuts.json','extra-cuts.json']:
    d=json.loads((H/name).read_text())
    all_ranges.extend(dict(row,source=d['source'],source_sha256=d['source_sha256']) for row in d['ranges'])
all_ranges.extend(proof['extra_source_ranges']);assert len(all_ranges)==30
for row in all_ranges:
    raw=(R/row['source']).read_bytes();assert sha256(raw).hexdigest()==row['source_sha256'];e=ELFFile(BytesIO(raw));a=row['offset'];n=row['bytes']
    if e['e_type']=='ET_REL':part=e.get_section_by_name(row['section']).data()[a:a+n]
    else:
        s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']);at=s['p_offset']+a-s['p_vaddr'];part=raw[at:at+n]
    assert len(part)==n and sha256(part).hexdigest()==row['sha256']
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
profile=json.loads((H/'FX3-default-profile-candidate.json').read_text());assert [profile['SIO_channel'],profile['GPIO_portid'],profile['GPIO_bitnum'],profile['GPIO_open_mode']]==[0,4,2,2]
assert not profile['runtime_verified'] and not profile['executable_payload'] and not profile['device_operation_authorized'] and not profile['independent_restore_proven']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST and not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes();assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text());assert len(old['requirements'])==16 and native['goal']['status']=='active' and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='OFFICIAL_MAIN_LOCAL_AND_CP_RECORD_ROUTES_BOUND',previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Official queue callback and operation4 dispatch now tied to local Data state. First record is local default; CP transfer explicitly walks to aligned record1. Classic public AP defaults0/4/2 are evidence-based, not selected by resemblance. Candidate remains nonexecutable, no same-body configuration or recovery proven.',
    correction='207 w2=4 is operation selector, not byte length; prior sealed files retained',limits=proof['limits'],
    root01='195 specific approval pending; no launch/job or repeated question',Sony_code_or_guest_execution=False,root_or_device_operations=0,goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_SOURCE_BOUND_LOCAL_CP_RECORD_ROUTING',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=49,
    official7_02_main_members_rebound=5,original_source_ranges_reverified=30,public_template_layout_cases=11,
    queue='0x003e014d',operation4_maps_to_read4=True,operation4_not_a_length=True,public_AP_record=0,public_CP_record=1,
    AP_default_SIO_port_bit=[0,4,2],runtime_settings_or_hardware_execution_proven=False,
    nonexecutable_profile_candidate=True,host01_bundle_sha256_unchanged=HOST,host01_job_absent=True,release0_4_zip_unchanged=True,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0))
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Official main backup.ko queue0x3e014d/operation4 actual receiver bound. Local Data_init uses first record; CP transfer explicitly uses aligned record1.11template layouts match; public APdefaults0/4/2, CPdefaults5/4/30.30original ranges,5main members rebound. Wrapper4 is operation selector, not length. No Sony/guest/root/device actions;195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification'];new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('208绑官方backup.ko队列3e014d与操作4实际分派、本地Data首记录与CP索引1对齐下一记录；11模板边界吻合，AP默认0/4/2已确定，非实机设置。30原范围/5主系统原件；修正207的w2=4是操作号非长度。无设备/root/guest，16要求/授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',routing=REL+'/record-routing-proof.json',capture=REL+'/source-capture.json',candidate=REL+'/FX3-default-profile-candidate.json',refinements=REL+'/analysis-refinements.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage208_Backup_local_CP_record_routing']=ev
new['recovery_Backup_local_CP_record_routing']={**ev,'official_main_public_local_record':0,'official_main_public_CP_record':1,'public_AP_default_SIO_port_bit':[0,4,2],
    'actual_current_body_Backup_or_pin_configuration_proven':False,'same_body_backup_or_independent_restore_proven':False}
new['recovery_Backup_template_and_GPIO_configuration']['public_template_record_roles_resolved_in_stage208']=True
new['corrections_to_prior_stage']['stage207_wrapper_w2_selector']={'old_label':'4-byte length','correct_meaning':'operation selector4; actual dispatch calls Backup_read_4Byte; w3=1 is argument count','old_sealed_files_preserved':True,'evidence':REL+'/record-routing-proof.json'}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准、不启动、不重问；主机试验不自动放行相机。',
    '以经典AP默认SIO0/GPIO4,2为静态候选，核对当前官方驱动的SIO/GPIO调用合同与恢复载荷时钟/启动依赖；默认参数相同仍非同机设置或运行证明，不生成可执行恢复载荷冒充已适配。',
    '保留当前p1/ROM及独立AP入口、MCU状态/CRC/回复时效、同机boot0/p1备份、逆写与独立救砖实测缺项；完整16要求及真实MAIN1080p29.97 HEVC长录待验收。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib);marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3 Backup本地与CP记录选择](<'+REL+'/README.md>)：官方队列/操作4分派与首记录本地、第二记录CP已绑，AP默认0/4/2；11模板/30原范围/5原件核回。候选不可执行，实机设置与独立恢复未验；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text;ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage208-Backup-local-CP-record-routing-v1',created_utc=now,previous_manifest_sha256=PREV,previous_members_reverified=49,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,new_approval_granted=False,
    Sony_code_or_guest_execution=False,root_or_device_operations=0,native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),source_ranges=30,main_members=5,local_default_record=0,CP_default_record=1,
    requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
