"""Rebind offline artifacts and register stage213 without changing authority."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from datetime import datetime,timezone
import ast,itertools,json,mmap,os,plistlib,re,stat,struct,subprocess
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2];REL=str(H.relative_to(R))
P=B/'stage212-official-boot-backup-generator'
PREV='52dd773a26235e98d80d3f8d6df41f0120d63871e5f9d217b1a9db2a9f18fb02'
HOST='00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(path):return sha256(path.read_bytes()).hexdigest()
def volume():
    x=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert x['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(name,x):(H/name).open('x').write(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
volume();assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json')==PREV
prior=json.loads((P/'final-receipt.json').read_text());assert len(prior['files'])==66
for row in prior['files']:
    p=R/row['path'];assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
parser=B/'stage2/extraction/read_filesystems.py'
assert digest(parser)=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
nodes=[x for x in ast.parse(parser.read_text()).body if isinstance(x,ast.ClassDef) and x.name in ['Ext2','FAT16']]
ns=dict(struct=struct,itertools=itertools,mmap=mmap)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed host filesystem classes>','exec'),ns)
image=B/'stage2/extraction/nflasha3.img'
assert digest(image)=='ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568'
fat=ns['FAT16'](image)
try:
    ent=next(x for x in fat.walk() if x['path']=='/initrd.img')
    data=fat.data(ent['cluster'],ent['size'])
    initrd=B/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/p3-main/initrd.img'
    assert data==initrd.read_bytes() and sha256(data).hexdigest()=='5ba4076f0f0765d57767736c824b12ed345a38cbb6541d61546570a4470c9f52'
finally:fat.b.close();fat.f.close()
fs=ns['Ext2'](initrd);ent={x['path']:x for x in fs.walk()};count=0
try:
    for name in ['driver-source-capture.json','devno-source-capture.json']:
        cap=json.loads((H/name).read_text());assert digest(R/cap['source_image'])==cap['source_sha256']
        for row in cap['files']:
            original=fs.data(ent[row['path_in_image']]['inode'])
            assert original==(R/row['output']).read_bytes()
            assert len(original)==row['bytes'] and sha256(original).hexdigest()==row['sha256'];count+=1
finally:fs.b.close();fs.f.close()
assert count==6
proof=json.loads((H/'AP-storage-contract-proof.json').read_text());assert len(proof['raw_ranges'])==11
for row in proof['raw_ranges']:
    src=R/row['source'];raw=src.read_bytes();assert sha256(raw).hexdigest()==row['source_sha256']
    off=row['file_offset'];piece=raw[off:off+row['bytes']]
    assert piece==(R/row['raw']).read_bytes() and sha256(piece).hexdigest()==row['sha256']
    with src.open('rb') as f:
        elf=ELFFile(f);sec=elf.get_section_by_name(row['section'])
        assert off==sec['sh_offset']+row['section_offset']
for row in proof['source_lines']:
    assert (H/row['path']).read_text().splitlines()[row['line']-1]==row['text']
assert [(x['name'],x['major'],x['first_minor']) for x in proof['nodes'][1:3]]==[('nflashaB0',252,126),('nflashaB1',252,127)]
assert proof['boot_capacity_runtime_value'] is None and not proof['boot_capacity_fixed_4MiB_proven']
assert proof['boot_descriptors_software_crypt_callback_cleared'] and not proof['lower_transfer_crypto_or_whole_boot_rawness_closed']
for name in ['GPL-source-capture.json','GPL-devnode-source-capture.json']:
    cap=json.loads((H/name).read_text())
    assert digest(R/cap['archive'])==cap['archive_sha256']=='bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f'
    for row in cap['files']:
        assert digest(R/row['output'])==row['sha256'] and (R/row['output']).stat().st_size==row['bytes']
hist=json.loads((H/'historical-AP-asset-recheck.json').read_text())
assert [x['version'] for x in hist['packages']]==['2.04','2.05']
assert [x['outer_tar_members'] for x in hist['packages']]==[135,134]
for row in hist['packages']:
    src=R/row['source'];assert src.stat().st_size==row['source_bytes'] and digest(src)==row['source_sha256']
    assert not row['AP_boot_asset_name_matches'] and len(row['NOR_members'])==4
    assert row['checked_plaintext_blocks']==262 and not row['all_plaintext_blocks_checked']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for p in H.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
plan=json.loads((H/'AP-boot-capture-contract-candidate.json').read_text())
for k in ['executable_payload','new_device_backend','camera_operation_authorized','device_read_or_write_performed','persistent_write_release']:assert not plan[k]

canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert len(old['requirements'])==16 and native['goal']['status']=='active' and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
verification=dict(status='PASS_CURRENT_AP_STORAGE_AND_HISTORICAL_INVENTORY_REBIND',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=66,
    p3_image_sha256='ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568',
    initrd_reextracted_from_original_FAT=True,original_initrd_files_reextracted=6,
    original_ELF_section_ranges=11,source_line_pins=16,independent_word_checks=4,independent_relocation_checks=3,
    boot0_public_main_rdev=[252,126],boot1_public_main_rdev=[252,127],
    actual_geometry_or_current_body_p1_identity_measured=False,
    lower_transfer_crypto_or_whole_boot_rawness_closed=False,
    historical_packages=2,top_tar_member_counts=[135,134],NOR_inner_member_counts=[4,4],
    visited_plaintext_blocks_per_package=262,all_plaintext_rechecked=False,
    GPL_layout_reference_only=True,release04_unchanged=True,root01_bundle_unchanged=True,root01_job_absent=True,
    all16_requirements_and_authorizations_unchanged=True,
    Sony_code_or_guest_execution=False,root_or_device_operations=0,persistent_write_release=False)
if (H/'verification-receipt.json').exists():
    saved=json.loads((H/'verification-receipt.json').read_text())
    assert {k:v for k,v in saved.items() if k!='created_utc'}=={k:v for k,v in verification.items() if k!='created_utc'}
else:put('verification-receipt.json',verification)
new=deepcopy(old);new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',
    goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Bound current7.02 main p3 devno/emmc modules: B0/B1 block nodes252:126/127, descriptor kinds1/2 and dynamic boot capacityu8<<17; do not assume A7IV4MiB or formatter2MiB capture size. Boot software crypt callback cleared and direct sequence read shown; lower crypto/rawness remains unclosed. Reindexed original2.04/2.05 top135/134 and NOR4/4 members, no AP asset names in reviewed scope.6originals,11ranges,16source lines,4raw-word/3reloc checks. No Sony/guest/root/device action;16requirements,195 pending andrelease04 unchanged.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],
    status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification']
new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('213由7.02 p3原initrd绑定devno/emmc：B0/B1块节点252:126/127、内部类型1/2，容量u8<<17而非固定4MiB；启动描述符无软件crypt回调，低层完整raw视图仍未闭合，2MiB formatter窗口不充整区备份。两历史原包135/134顶层和4/4 NOR内层重查无AP命名载荷，范围不作全局缺失证明。6原件/11范围/16行/4原字+3重定位；无设备/root/guest，16要求及授权保持。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',proof=REL+'/AP-storage-contract-proof.json',
    historical=REL+'/historical-AP-asset-recheck.json',driver_capture=REL+'/driver-source-capture.json',
    devno_capture=REL+'/devno-source-capture.json',GPL=REL+'/GPL-source-capture.json',
    candidate=REL+'/AP-boot-capture-contract-candidate.json',scope=REL+'/implementation-review.json',
    web_review=REL+'/web-source-review.json',Sony_code_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage213_AP_boot_devices_and_capacity']=ev
new['recovery_AP_boot_devices_and_capacity']={**ev,
    'public_main_boot0_rdev':[252,126],'public_main_boot1_rdev':[252,127],
    'boot_capacity_formula':'u8 state+dc <<17; selected boot start_sector0',
    'actual_boot_capacity_bytes':None,'fixed_4MiB_or_formatter_2MiB_size_assumed':False,
    'software_crypt_callback_cleared_in_selected_boot_init':True,
    'lower_transfer_crypto_or_whole_boot_rawness_closed':False,
    'current_body_p1_driver_identity_attested':False,
    'historical_top_member_counts':[135,134],'historical_NOR_inner_counts':[4,4],
    'AP_boot_asset_names_in_reviewed_historical_member_scope':False,
    'same_body_backup_or_independent_restore_proven':False}
new['provenance_refinements'].append({
    'stage213_GPL_node_table_scope':True,
    'evidence':REL+'/AP-storage-contract-proof.json','GPL_shared_layout_used':True,
    'GPL_platform_node_table_is_not_current_module_table':True,
    'current_node_names_numbers_from_relocated_original_devno_module':True})
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答；不将继续当批准，不启动或重问，不扩大相机权限。',
    '沿当前7.02主系统emmc.ko的sequence read→.text+10EC0下层数据/crypto分派及boot容量字段生产者继续查，闭合备份视图和容量来源；当前B0/B1节点与空软件crypt回调不充完整raw读取或同机p1身份。只做文件静态分析。',
    '以整区实际容量、环境身份与内容回读合同推进既有受限采集工作器适配；保留同机boot0/p1/完整配置和独立AP恢复入口、回写/冷启动/故障恢复验收。其他经典官方历史包AP组件检索仍可继续，不能把两过渡包无AP名称当全局不存在。全部16要求和真实MAIN1080p29.97 HEVC长录保持。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3 AP启动区设备与动态容量](<'+REL+'/README.md>)：当前p3原驱动B0/B1节点252:126/127与容量u8×128KiB已绑，不能套4MiB/2MiB；启动区无软件crypt回调，低层完整视图未闭合。两旧包135/134清单及NOR4/4重核，6原件/11范围，195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link and link!='final-receipt.json':assert (H/link.strip('<>')).resolve().exists(),link
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name,expected in [(canonical,after,'.goal.tmp',before),(index,ia,'.index.tmp',ib)]:
    assert dest.read_bytes()==expected;p=H/name
    with p.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage213-AP-boot-device-and-asset-search-v1',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=66,files=members,member_count=len(members),
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),mutable_heads_not_manifest_members=True,
    root01_bundle_sha256_unchanged=HOST,new_approval_granted=False,Sony_code_or_guest_execution=False,root_or_device_operations=0,
    native_goal_observed='active',native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),
    raw_ranges=11,original_initrd_files=6,historical_packages=2,requirements_unchanged=16,authorizations_unchanged=True,device_operations=0)))
