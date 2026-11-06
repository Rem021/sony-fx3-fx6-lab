"""Verify captured public boot references and register their limited applicability."""
from pathlib import Path
from hashlib import sha256, sha1
from copy import deepcopy
from datetime import datetime, timezone
import json, os, plistlib, re, stat, struct, subprocess

H = Path(__file__).resolve().parent
B = H.parent
R = H.parents[2]
P = B / 'stage203-WBI-layout-and-early-memory'
REL = str(H.relative_to(R))
PREV = '82624712711670da1c5bfab37b341a266672ae743a96d0546fedd31246bfe8e6'
HOST = '00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'
def digest(p):
    return sha256(p.read_bytes()).hexdigest()
def put(name, obj):
    with (H / name).open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
def volume():
    j = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert j['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
volume()
assert not (H / 'final-receipt.json').exists() and digest(P / 'final-receipt.json') == PREV
prior = json.loads((P / 'final-receipt.json').read_text())
assert len(prior['files']) == 36
for row in prior['files']:
    p = R / row['path']
    assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size == row['bytes'] and digest(p) == row['sha256']
capture = json.loads((H / 'source-capture.json').read_text())
assert len(capture['files']) == 11
assert digest(H / 'upstream-tree.json') == capture['tree_sha256']
tree = json.loads((H / 'upstream-tree.json').read_text())
assert not tree['truncated'] and len(tree['tree']) == 98
for row in capture['files']:
    data = (R / row['output']).read_bytes()
    assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
    blob = sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert blob == row['git_blob_sha1'] == next(r['sha'] for r in tree['tree'] if r['path'] == row['path'])
proof = json.loads((H / 'AP-reference-boot-proof.json').read_text())
binding = json.loads((H / 'public-SRAM-binding.json').read_text())
image = (R / proof['SRAM_source']).read_bytes()
assert sha256(image).hexdigest() == proof['SRAM_sha256'] == binding['SRAM_sha256']
assert digest(H / 'reference/emmc_boot/emmc_boot0.bin') == proof['boot0_sha256'] == binding['boot0_sha256']
assert digest(H / 'reference/bootrom/CXD90057_Mira_0xFFFF0000.bin') == proof['AP_ROM_sha256'] == binding['AP_ROM_sha256']
assert len(proof['selected_original_ranges']) == 8 and proof['selected_partition'] == 1
for row in proof['selected_original_ranges']:
    a, z = int(row['start'], 16) - 0xfe040000, int(row['end_exclusive'], 16) - 0xfe040000
    data = image[a:z]
    assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
for row in proof['sequence_entries']:
    a = int(row['address'], 16) - 0xfe040000
    callback, flags = struct.unpack_from('<QQ', image, a)
    label = image[a + 16:a + 32].split(b'\0', 1)[0].decode('ascii')
    assert (hex(callback), hex(flags), label) == (row['callback'], row['flags'], row['label'])
for row in proof['boot_file_paths']:
    a = int(row['address'], 16) - 0xfe040000
    assert image[a:].split(b'\0', 1)[0].decode('ascii') == row['path']
comparison = proof['FX3_NOR_comparison']
other = (R / comparison['source']).read_bytes()
assert sha256(other).hexdigest() == comparison['sha256']
assert image[0x9000:0x9080] == other[:128] and image.find(other) == -1
assert digest(B / 'stage195-root-host-validation-plan/approval-bundle.json') == HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R / 'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip') == '43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)', (H / 'README.md').read_text()):
    if '://' not in link:
        assert (H / link.strip('<>')).resolve().exists(), link
canonical = B / 'GOAL_STATUS.json'
before = (H / 'goal-status-before.json').read_bytes()
assert before == canonical.read_bytes() == (P / 'goal-status-after.json').read_bytes()
old = json.loads(before)
native = json.loads((H / 'native-goal-observed.json').read_text())
assert native['goal']['status'] == 'active'
assert len(old['requirements']) == 16 and not old['prepared_root_host_trial']['explicitly_authorized']
now = datetime.now(timezone.utc).isoformat()
put('implementation-review.json', dict(status='PUBLIC_REFERENCE_AP_BOOT0_AND_UPDATER_PARTITION_PATH_BOUND',
    prior_goal_turn_classification='progress', prior_basis='203 completed WBI layout/resume/eMMC bindings; not a wait or repeated status',
    this_goal_turn_classification='progress',
    next_action_changed='Actual public A7IV AP boot0/ROM/SRAM now available locally and bound; use real mode3/partition1 code as reference for FX3-specific hardware differences instead of assuming the public source lacks boot0.',
    limits=['reference A7IV2.00 is not current FX3 AP ROM/boot0 or installed p1 identity',
            'mode3 path has runtime flags/earlier steps; static consumer linkage is not a successful boot or restore',
            'generic entry128 equality does not establish same program, same board initialization or safe cross-model loading',
            'no independent FX3 recovery, actual inverse write, MAIN HEVC or long-record acceptance'],
    root01='195 specific answer pending; no job/admin operation or repeated question',
    original_or_guest_executions=0, root_or_device_operations=0,
    goal_complete=False, persistent_write_release=False))
put('verification-receipt.json', dict(status='PASS_PUBLIC_REFERENCE_BINDINGS', created_utc=now,
    previous_manifest_sha256=PREV, previous_members_reverified=36, public_files_reverified=11,
    full_git_tree_entries=98, truncated=False, decoded_public_SRAM_bytes=190464,
    original_ranges_reverified=8, boot_file_path_bindings=5,
    sequence_callback_layout_verified=True, same_body_boot0_obtained=False,
    release0_4_zip_unchanged=True, host01_bundle_sha256_unchanged=HOST,
    new_approval_granted=False, original_or_guest_executions=0, root_or_device_operations=0))
new = deepcopy(old)
new.update(updated_utc=now, latest_stage=H.name, goal_manager_status='active', goal_manager_status_last_observed='active',
           native_goal_state_not_modified=True,
           research_activity='Obtained pinned public A7IV2.00 AP BootROM,4MiBboot0 and190464B SRAM. Own host-data decrypt matches whole SRAM; raw instructions/table consumer bind mode3 to updater sequence, partition1 FAT and5boot files.8ranges fixed; reference only, not FX3 body. No original/guest/root/device actions;195 pending.')
new['current_native_goal_observation'] = dict(receipt=REL + '/native-goal-observed.json', observed_utc=native['observed_utc'],
    status='active', source='native get_goal read only', device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
new['progress_audit']['classification'] = 'progress'
new['progress_audit']['basis'].append('204成功取得公共A7IV AP ROM/boot0/SRAM，11文件绑定blob，190464字节全量对应；模式3→实际32B序列表→p1 FAT/5启动文件已绑原指令。旧本地未含bin不是上游不存在。仅参考，FX3同机启动原件/独立恢复仍缺；无设备/root/guest。')
ev = dict(readme=REL + '/README.md', verification=REL + '/verification-receipt.json',
    source_capture=REL + '/source-capture.json', reference=REL + '/AP-reference-boot-proof.json',
    SRAM_binding=REL + '/public-SRAM-binding.json', scope=REL + '/implementation-review.json',
    web_review=REL + '/web-source-review.json', original_or_guest_execution=False, root_or_device_operations=0)
new['latest_stage_evidence']['stage204_public_AP_boot_reference'] = ev
new['recovery_public_AP_boot_reference'] = {**ev, 'reference_model':'ILCE-7M4 2.00',
    'reference_commit':capture['commit'], 'public_AP_boot0_obtained':True,
    'reference_mode3_to_partition1_path_bound':True, 'FX3_same_body_AP_boot0_obtained':False,
    'FX3_independent_entry_or_inverse_restore_proven':False}
new['next_safe_offline_actions'] = [
    '195仅主机root01原具体问题待答，不把继续当批准，不启动、不重问；其通过也不会自动放行相机。',
    '对照本轮实际AP启动原件与FX3当前DTB/内核资料的内存、eMMC、USB和看护配置，明确参考载荷可复用部分与型号差异；不按相同entry128猜整套兼容。',
    'FX3原机AP ROM/boot0、当前p1身份和独立逆写/冷恢复仍须实际证据；不将A7IV参考冒充同机备份，不上传外机载荷。保留16要求及真实1080p29.97 HEVC主录/长录。']
for key in ['authorization', 'requirements', 'prepared_first_device_trial', 'research_priority', 'current_native_owner_channel_candidate', 'prepared_root_host_trial']:
    assert new[key] == old[key], key
assert not new['goal_complete'] and not new['persistent_write_release']
after = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
(H / 'goal-status-after.json').open('xb').write(after)
index = R / 'README.md'
ib = index.read_bytes()
(H / 'readme-rebased-before.md').open('xb').write(ib)
marker = '## 相机与固件研究\n'
entry = '- [2026-10-29 FX3适配用公开AP启动参考](<' + REL + '/README.md>)：实际取得A7IV ROM/boot0/SRAM；190464字节全量绑定，模式3→p1启动文件已追到原码，8切片。仅参考，非FX3同机备份；195待答，无设备/root/guest动作。'
text = ib.decode()
assert text.count(marker) == 1 and entry not in text
ia = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
(H / 'readme-after.md').open('xb').write(ia)
volume()
assert canonical.read_bytes() == before and index.read_bytes() == ib, 'concurrent CAS change'
for dest, content, name in [(canonical, after, '.goal.tmp'), (index, ia, '.index.tmp')]:
    p = H / name
    with p.open('xb') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(p, dest)
members = [dict(path=str(p.relative_to(R)), bytes=p.stat().st_size, sha256=digest(p))
           for p in sorted(H.rglob('*')) if p.is_file() and not p.is_symlink()]
put('final-receipt.json', dict(schema='fx3-stage204-public-AP-reference-v1', created_utc=now,
    previous_manifest_sha256=PREV, previous_members_reverified=36, files=members, member_count=len(members),
    mutable_heads_not_manifest_members=True, goal_before_sha256=sha256(before).hexdigest(), goal_after_sha256=sha256(after).hexdigest(),
    host01_bundle_sha256_unchanged=HOST, new_approval_granted=False, original_or_guest_execution=False,
    root_or_device_operations=0, native_goal_observed='active', native_goal_status_changed_by_assistant=False,
    goal_complete=False, persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H / 'final-receipt.json'), members=len(members),
    public_reference_files=11, AP_updater_reference_bound=True, FX3_same_body_boot0_obtained=False,
    requirements_unchanged=16, all_authorizations_unchanged=True, new_camera_operations=0)))
