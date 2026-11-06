"""Verify static hardware correspondences and preserve all device gates."""
from pathlib import Path
from hashlib import sha256, sha1
from copy import deepcopy
from datetime import datetime, timezone
import json, os, plistlib, re, stat, struct, subprocess, tarfile
H = Path(__file__).resolve().parent
B = H.parent
R = H.parents[2]
P = B/'stage204-public-AP-boot-reference'
REL = str(H.relative_to(R))
PREV = 'abc88a1a2fe6a04b7d80b278b6448190af4b1e7db392b6e5a46ffe13dffc0a14'
HOST = '00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p): return sha256(p.read_bytes()).hexdigest()
def put(n, value):
    with (H/n).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
def volume():
    assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume()
assert not (H/'final-receipt.json').exists() and digest(P/'final-receipt.json') == PREV
previous = json.loads((P/'final-receipt.json').read_text())
assert len(previous['files']) == 50
for row in previous['files']:
    p = R/row['path']
    assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
capture = json.loads((H/'payload-source-capture.json').read_text())
tree = json.loads((P/'upstream-tree.json').read_text())
assert len(capture['files'])==47
for row in capture['files']:
    d = (R/row['output']).read_bytes()
    assert len(d)==row['bytes'] and sha256(d).hexdigest()==row['sha256']
    assert sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()==row['git_blob_sha1']==next(r['sha'] for r in tree['tree'] if r['path']==row['path'])
vendor = json.loads((H/'vendor-source-capture.json').read_text())
extra = json.loads((H/'clock-reset-source-capture.json').read_text())
archive = Path(vendor['archive'])
assert digest(archive)==vendor['sha256']==extra['archive_sha256']
items = {r['member']:r for r in vendor['files']+extra['files']}
assert len(items)==18
found = set()
with tarfile.open(archive, 'r|gz') as tf:
    for m in tf:
        if m.name not in items: continue
        row = items[m.name]
        d = tf.extractfile(m).read()
        assert d==(R/row['output']).read_bytes() and len(d)==row['bytes'] and sha256(d).hexdigest()==row['sha256']
        found.add(m.name)
assert found==set(items)
dtcap = json.loads((H/'DTB-source-capture.json').read_text())
assert digest(R/dtcap['output'])==digest(Path(dtcap['source']))==dtcap['sha256']
dt = json.loads((H/'DTB-decoded.json').read_text())
assert dt['source_sha256']==dtcap['sha256'] and len(dt['nodes'])==68 and dt['total_bytes']==16875
profile = json.loads((H/'hardware-profile-comparison.json').read_text())
assert len(profile['resource_comparisons'])==9 and len(profile['USB_clock_bindings'])==4
assert len(profile['source_line_pins'])==28 and profile['USB_clock_gate_mask']=='0xf000' and profile['USB_reset_ids']==[11,10,9,8]
for row in profile['source_line_pins']:
    p = R/row['source'];d=p.read_bytes();lines=d.splitlines(keepends=True)
    assert sha256(d).hexdigest()==row['source_sha256']
    part=b''.join(lines[row['line_start']-1:row['line_end_inclusive']])
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['selected_sha256']
wdt = json.loads((H/'Darwin-WDT-source-proof.json').read_text())
d=(R/wdt['source']).read_bytes()
assert sha256(d).hexdigest()==wdt['source_sha256'] and len(wdt['selected_ranges'])==10
for row in wdt['selected_ranges']:
    part=d[int(row['start'],16)-0x4200:int(row['end_exclusive'],16)-0x4200]
    assert len(part)==row['bytes'] and sha256(part).hexdigest()==row['sha256']
assert struct.unpack_from('<I',d,0x65b4-0x4200)[0]==0x200026fc
assert len(wdt['reload_source_examples'])==3 and not wdt['actual_live_counter_state_read']
for row in wdt['reload_source_examples']:
    pc=int(row['base_load'],16);half=struct.unpack_from('<H',d,pc-0x4200)[0]
    pool=((pc+4)&~3)+(half&255)*4
    assert pool==int(row['base_pool'],16) and struct.unpack_from('<I',d,pool-0x4200)[0]==0x20000000
    at=int(row['byte_load'],16)-0x4200;first,second=struct.unpack_from('<HH',d,at)
    assert first&15==(half>>8)&7 and second&4095==0x3c+row['slot']
assert digest(B/'stage195-root-host-validation-plan/approval-bundle.json')==HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R/'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip')=='43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)',(H/'README.md').read_text()):
    if '://' not in link: assert (H/link.strip('<>')).resolve().exists(),link
canonical=B/'GOAL_STATUS.json';before=(H/'goal-status-before.json').read_bytes()
assert before==canonical.read_bytes()==(P/'goal-status-after.json').read_bytes()
old=json.loads(before);native=json.loads((H/'native-goal-observed.json').read_text())
assert native['goal']['status']=='active' and len(old['requirements'])==16 and not old['prepared_root_host_trial']['explicitly_authorized']
now=datetime.now(timezone.utc).isoformat()
put('implementation-review.json',dict(status='STATIC_HARDWARE_RESOURCES_AND_CURRENT_MCU_COUNTER_FIELDS_BOUND',
    previous_goal_turn_classification='progress',this_goal_turn_classification='progress',
    next_action_changed='Do not require complete DDR training for the reference SRAM-only layout.9static resources/USB clock-reset mapping and current FX3 MCU counter/reload fields now correspond. Next verify current command16 and SIO/CS sources instead of guessing board pins or feeding counters.',
    limits=profile['unresolved'],MCU_assumptions=wdt['limits'],
    root01='195 specific approval pending; no repeated question, job or admin launch',
    source_payload_compiled_uploaded_or_run=False, original_or_guest_executions=0, root_or_device_operations=0,
    goal_complete=False,persistent_write_release=False))
put('verification-receipt.json',dict(status='PASS_SOURCE_BOUND_STATIC_COMPARISON',created_utc=now,
    previous_manifest_sha256=PREV,previous_members_reverified=50,payload_files_reverified=47,
    GPL_files_reverified_against_archive=18,DTB_bytes=16875,DTB_nodes=68,
    hardware_resource_comparisons=9,USB_clock_bindings=4,source_line_ranges=28,MCU_original_ranges=10,
    same_body_boot0_p1_or_live_watchdog_state_obtained=False,host01_bundle_sha256_unchanged=HOST,
    release0_4_zip_unchanged=True,new_approval_granted=False,original_or_guest_executions=0,root_or_device_operations=0))
new=deepcopy(old)
new.update(updated_utc=now,latest_stage=H.name,goal_manager_status='active',goal_manager_status_last_observed='active',native_goal_state_not_modified=True,
    research_activity='Bound9reference resources to current package DTB or explicitly labeled7.00 GPL,4USB clock mappings/reset IDs, SRAM-only link layout. Current FX3 MCU counter200026FC and3reload source examples3C/3D/3E bound by raw Thumb fields/10ranges;28source-line pins. No compiled/uploaded payload or original/guest/root/device actions.195 pending.')
new['current_native_goal_observation']=dict(receipt=REL+'/native-goal-observed.json',observed_utc=native['observed_utc'],status='active',source='native get_goal read only',device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification']=old['progress_audit']['classification']
new['progress_audit']['classification']='progress'
new['progress_audit']['basis'].append('205将参考载荷9项资源与FX3包DTB/明确标记7.00源码对应，4USB时钟/复位已绑；SRAM链接布局不要求完整DDR训练。当前MCU计数表及3重装来源静态匹配，28行范围/10原切片。下一项CMD16/SIO引脚；无实机/root/guest，16要求与授权不变。')
ev=dict(readme=REL+'/README.md',verification=REL+'/verification-receipt.json',profile=REL+'/hardware-profile-comparison.json',
    MCU=REL+'/Darwin-WDT-source-proof.json',DTB=REL+'/DTB-decoded.json',scope=REL+'/implementation-review.json',web_review=REL+'/web-source-review.json',original_or_guest_execution=False,root_or_device_operations=0)
new['latest_stage_evidence']['stage205_FX3_hardware_profile_comparison']=ev
new['recovery_FX3_hardware_profile_comparison']={**ev,'static_resource_correspondences':9,'reference_SRAM_layout_does_not_require_complete_DDR_training':True,
    'current_MCU_counter_and3reload_source_examples_bound':True,'actual_entry_SIO_or_keepalive_proven':False,'same_body_boot0_p1_identity_or_independent_restore_proven':False}
new['next_safe_offline_actions']=[
    '195仅主机root01原具体问题待答，不把继续当批准，不启动或重问；普通主机验证不自动放行相机。',
    '下一项核对当前FX3 MCU的读命令0x16分派/帧约定及计数表访问，再追SIO/CS配置来源；未证明链路前不生成供执行的引脚或保活写参数。',
    '保留ROM/独立启动桥、CP复位、实际可用SRAM、同机boot0/p1、逆写/冷恢复等缺项。通用MMIO对应不代表可上传A7IV载荷。16要求及MAIN1080p29.97 HEVC/长录验收不缩减。']
for key in ['authorization','requirements','prepared_first_device_trial','research_priority','current_native_owner_channel_candidate','prepared_root_host_trial']:
    assert new[key]==old[key],key
assert not new['goal_complete'] and not new['persistent_write_release']
after=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(H/'goal-status-after.json').open('xb').write(after)
index=R/'README.md';ib=index.read_bytes();(H/'readme-rebased-before.md').open('xb').write(ib)
marker='## 相机与固件研究\n'
entry='- [2026-10-29 FX3恢复载荷硬件对应与看护字段](<'+REL+'/README.md>)：9资源/4USB时钟静态对应，参考布局只用SRAM；当前MCU计数表及3重装来源已绑，28行范围/10原切片。链路与实机恢复未验；195待答，无设备/root/guest动作。'
text=ib.decode();assert text.count(marker)==1 and entry not in text
ia=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(H/'readme-after.md').open('xb').write(ia)
volume();assert canonical.read_bytes()==before and index.read_bytes()==ib,'concurrent CAS change'
for dest,content,name in [(canonical,after,'.goal.tmp'),(index,ia,'.index.tmp')]:
    p=H/name
    with p.open('xb') as f: f.write(content);f.flush();os.fsync(f.fileno())
    os.replace(p,dest)
members=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json',dict(schema='fx3-stage205-static-hardware-comparison-v1',created_utc=now,previous_manifest_sha256=PREV,
    previous_members_reverified=50,files=members,member_count=len(members),mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(),goal_after_sha256=sha256(after).hexdigest(),host01_bundle_sha256_unchanged=HOST,
    new_approval_granted=False,original_or_guest_execution=False,root_or_device_operations=0,native_goal_observed='active',
    native_goal_status_changed_by_assistant=False,goal_complete=False,persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H/'final-receipt.json'),members=len(members),resource_correspondences=9,
    MCU_ranges=10,requirements_unchanged=16,all_authorizations_unchanged=True,device_operations=0)))
