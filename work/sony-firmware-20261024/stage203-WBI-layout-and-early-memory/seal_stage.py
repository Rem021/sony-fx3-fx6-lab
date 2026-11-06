"""Recheck saved stock images and publish the bounded WBI result; no device I/O."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util, json, mmap, os, plistlib, re, stat, struct, subprocess, tarfile
from elftools.elf.elffile import ELFFile

H = Path(__file__).resolve().parent
B = H.parent
R = B.parents[1]
P = B / 'stage202-update-transition-and-restart'
REL = str(H.relative_to(R))
PREV = '987c385746b273dca77ef2da4abee1381c21034c9481983c491360556a47b693'
HOST = '00f983286fea58a429ff829887a1a65230cff817b51a4b5447c1a63b1a47f1d0'

def digest(p):
    return sha256(p.read_bytes()).hexdigest()

def put(name, value):
    with (H / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def fullpath(s):
    p = Path(s)
    return p if p.is_absolute() else R / p

def volume():
    info = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert info['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

volume()
assert not (H / 'final-receipt.json').exists()
assert digest(P / 'final-receipt.json') == PREV
prior = json.loads((P / 'final-receipt.json').read_text())
assert len(prior['files']) == 61
for row in prior['files']:
    p = R / row['path']
    assert stat.S_ISREG(p.lstat().st_mode)
    assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256']

audit = json.loads((H / 'WBI-layout-audit.json').read_text())
rows = audit['sections']
assert len(rows) == 1399 and audit['earlier_stage9_map_reverified']
source = Path(audit['source'])
with source.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
    assert sha256(raw).hexdigest() == audit['source_sha256']
    magic, padding, *header = struct.unpack_from('<4sI10Q', raw)
    assert magic == b'WBI2' and padding == 0
    assert list(audit['header'].values()) == header
    assert header[0] == 1399 and header[1] == 0 and header[4] == 512
    table = 512 + header[5]
    cursor = 512
    for n, row in enumerate(rows):
        vals = struct.unpack_from('<8Q', raw, table + n * 64)
        assert vals == tuple(row[k] for k in ['addr', 'rlen', 'cksum', 'flag', 'olen', 'virt', 'meta_cksum', 'padding'])
        check = 0x0f0f0f0f
        for val in vals[:6]:
            check ^= val
        assert check == vals[6] and row['index'] == n and row['file_offset'] == cursor
        assert row['virt'] == row['addr'] - 0x400000000 + 0xffffffc000000000
        assert row['addr'] % 4096 == 0 and row['olen'] % 4096 == 0 and row['olen'] > 0
        assert row['cksum'] == 0x0f0f0f0f and row['padding'] == 0
        assert (row['flag'], row['rlen']) in [(0, row['olen']), (1, 0)]
        assert cursor + row['rlen'] <= table
        actual = sha256(raw[cursor:cursor + row['rlen']]).hexdigest() if row['rlen'] else None
        assert actual == row['stored_sha256']
        cursor += row['rlen']
    assert cursor == table == audit['table_offset']
    assert sum(r['olen'] for r in rows) == header[9]
    assert sum(r['flag'] == 1 for r in rows) == 82
    ordered = sorted(rows, key=lambda r: r['addr'])
    assert all(a['addr'] + a['olen'] <= b['addr'] for a, b in zip(ordered, ordered[1:]))
    assert min(r['addr'] for r in rows) == 0x400001000
    assert max(r['addr'] + r['olen'] for r in rows) == 0x420000000
    assert [(a['index'], b['index']) for a, b in zip(rows, rows[1:]) if a['addr'] + a['olen'] > b['addr']] == [(1378, 1379)]
    for q in audit['address_queries']:
        a, z = int(q['start'], 16), int(q['end_exclusive'], 16)
        assert not [r for r in rows if r['addr'] < z and a < r['addr'] + r['olen']]
    end = table + 64 * len(rows)
    tail = raw[end:]
    assert end == audit['table_end_exclusive']
    assert len(tail) == audit['trailer']['bytes'] == 261632
    assert sum(x != 0 for x in tail) == audit['trailer']['nonzero_bytes'] == 2298
    assert sha256(tail).hexdigest() == audit['trailer']['sha256']
    anchors = 0
    for row in audit['exact_loader_copy_search']:
        p = Path(row['source'])
        data = p.read_bytes()
        assert sha256(data).hexdigest() == row['sha256'] and len(data) == row['bytes']
        assert raw.find(data) == -1 and row['exact_full_copy_offset'] is None
        for anchor in row['anchors128']:
            a = anchor['source_offset']
            assert raw.find(data[a:a + 128]) == -1 and not anchor['matched']
            anchors += 1
    assert anchors == 35
    corr = json.loads((H / 'kernel-image-correspondence.json').read_text())
    kernel = fullpath(corr['kernel_source']).read_bytes()
    assert sha256(kernel).hexdigest() == corr['kernel_sha256']
    row = rows[corr['section']]
    saved = raw[row['file_offset']:row['file_offset'] + row['rlen']]
    assert saved[:64] == kernel[:64] and kernel[56:60] == b'ARMd'
    assert sum(a != b for a, b in zip(saved, kernel)) == corr['different_bytes'] == 673
    assert sha256(saved).hexdigest() == corr['section_bytes_sha256']
    assert sha256(kernel[:len(saved)]).hexdigest() == corr['kernel_prefix_sha256']
    resume = json.loads((H / 'resume-source-slice.json').read_text())
    off = int(resume['file_offset'], 16)
    segment = raw[off:off + 64]
    assert segment.hex() == resume['bytes_hex'] and sha256(segment).hexdigest() == resume['sha256']
    assert segment == kernel[int(resume['comparison_kernel_offset'], 16):int(resume['comparison_kernel_offset'], 16) + 64]

reader = B / 'stage2/extraction/read_filesystems.py'
assert digest(reader) == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec = importlib.util.spec_from_file_location('saved_ext2', reader)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
capture = json.loads((H / 'emmc-provider-capture.json').read_text())
assert len(capture) == 2
src = fullpath(capture[0]['source_image'])
assert digest(src) == capture[0]['source_image_sha256']
fs = m.Ext2(src)
try:
    inv = {r['path']: r for r in fs.walk()}
    for row in capture:
        p = fullpath(row['output'])
        assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256']
        assert fs.data(inv[row['path']]['inode']) == p.read_bytes()
finally:
    fs.b.close()
    fs.f.close()
proof = json.loads((H / 'emmc-handoff-proof.json').read_text())
module = fullpath(proof['source_module']).read_bytes()
assert sha256(module).hexdigest() == proof['module_sha256']
elf = ELFFile(BytesIO(module))
for row in proof['selected_module_ranges']:
    data = elf.get_section_by_name(row['section']).data()[int(row['start'], 16):int(row['end_exclusive'], 16)]
    assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
def reloc(name, offset):
    sec = elf.get_section_by_name(name)
    symbols = elf.get_section(sec['sh_link'])
    r = next(r for r in sec.iter_relocations() if r['r_offset'] == offset)
    s = symbols.get_symbol(r['r_info_sym'])
    ix = s['st_shndx']
    return (elf.get_section(ix).name if isinstance(ix, int) else ix, s['st_value'] + r['r_addend'], s.name)
assert reloc('.rela__param', 0x48)[:2] == ('.bss', 0x528)
assert reloc('.rela__param', 0x38)[2] == 'param_ops_ulong'
section, offset, _ = reloc('.rela__param', 0x28)
assert elf.get_section_by_name(section).data()[offset:].split(b'\0', 1)[0] == b'tbl'
assert reloc('.rela.init.text', 0x928)[:2] == ('.bss', 0x1b8)
text = elf.get_section_by_name('.init.text').data()
assert struct.unpack_from('<I', text, 0x494)[0] & 0xff00001f == 0x58000016
word = struct.unpack_from('<I', text, 0x530)[0]
assert word & 0xffc003ff == 0xf94002c4 and ((word >> 10) & 0xfff) * 8 == 0x370
assert 0x1b8 + 0x370 == 0x528
assert 'tbl=0xFFFFFFC003E00000' in fullpath(proof['script']).read_text()
assert rows[1379]['virt'] == int(proof['tbl_argument'], 16) and rows[1379]['rlen'] == 0x22000

refs = json.loads((H / 'reference-source-capture.json').read_text())
warm = json.loads((H / 'warm-source-capture.json').read_text())
archive = Path(refs['archive'])
assert digest(archive) == refs['sha256'] == warm['archive_sha256']
with tarfile.open(archive, 'r:gz') as tf:
    for row in refs['captures'] + [warm]:
        p = fullpath(row['output'])
        assert p.stat().st_size == row['bytes'] and digest(p) == row['sha256']
        assert tf.extractfile(row['member']).read() == p.read_bytes()

assert digest(B / 'stage195-root-host-validation-plan/approval-bundle.json') == HOST
assert not os.path.lexists('/private/tmp/fx3-host-root-20261029-01')
assert digest(R / 'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip') == '43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
for link in re.findall(r'\]\(([^)]+)\)', (H / 'README.md').read_text()):
    if '://' not in link:
        assert (H / link.strip('<>')).resolve().exists(), link
canonical = B / 'GOAL_STATUS.json'
before = (H / 'goal-status-before.json').read_bytes()
assert canonical.read_bytes() == before == (P / 'goal-status-after.json').read_bytes()
old = json.loads(before)
native = json.loads((H / 'native-goal-observed.json').read_text())
assert native['goal']['status'] == 'active'
assert len(old['requirements']) == 16 and not old['prepared_root_host_trial']['explicitly_authorized']
now = datetime.now(timezone.utc).isoformat()
put('implementation-review.json', dict(
    status='WBI_SOURCE_LAYOUT_REVALIDATED_NO_INDEPENDENT_AP_BOOTLOADER_RECOVERED',
    findings=['stage9 map reverified:1399 metadata-XOR checks,82 zero-fill records, original ordering retained, no sorted physical overlap',
              'resume64 and Image-header64 match current package kernel; whole compared span still has673 differing bytes',
              'all declared physical destinations are above16GiB address base; none covers configured NOR address; tested exact loader copies/35 anchors absent',
              'script tbl address and actual module-param/consumer relocation bind record1379 to eMMC handoff data',
              '261632-byte trailer has2298 nonzero bytes and is retained as not fully interpreted'],
    limits=['reference GPL is7.00, not exact7.02 source or producer identity',
            'metadata XOR and stock-source hashes do not establish executable data checksums, safe boot or flash acceptance',
            'sample absence excludes only identical tested sequences; changed/other early code is not ruled out',
            'no current-body boot0/p1 backup, independent entry/inverse restore, cold boot or target MAIN recording acceptance'],
    root01='195 specific reply pending; no repeated question and fixed job absent',
    original_or_guest_executions=0, root_or_device_operations=0, goal_complete=False, persistent_write_release=False))
put('verification-receipt.json', dict(
    status='PASS_SAVED_WBI_AND_PROVIDER_BINDINGS', created_utc=now,
    previous_manifest_sha256=PREV, previous_members_reverified=61,
    WBI_records_rechecked=1399, stored_segment_hashes_rechecked=1317, zero_fill_records=82,
    loader_anchors_rechecked=35, resume64_equal=True, kernel_span_differences=673,
    captured_initrd_members_reverified=2, module_ranges_reverified=4,
    GPL_members_reverified_against_archive=4,
    host01_bundle_sha256_unchanged=HOST, release0_4_zip_unchanged=True,
    actual_recovery_or_device_recording_proven=False, new_approval_granted=False,
    original_or_guest_executions=0, root_or_device_operations=0))
new = deepcopy(old)
new.update(updated_utc=now, latest_stage=H.name, goal_manager_status='active',
           goal_manager_status_last_observed='active', native_goal_state_not_modified=True,
           research_activity='Revalidated existing1399-record WBI map against named Sony7.00 reference structure and actual7.02 source bytes; resume64 binds current Linux kernel,673 differences prevent whole-span identity. Driver tbl argument matches record1379. Preserved unexplained trailer; no independent AP boot0 recovered. No original/guest/root/device actions;195 pending.')
new['current_native_goal_observation'] = dict(receipt=REL + '/native-goal-observed.json', observed_utc=now,
    status='active', source='native get_goal read only', device_authorization_expanded=False)
new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
new['progress_audit']['classification'] = 'progress'
new['progress_audit']['basis'].append('203复核既有1399段及全部元数据XOR；恢复64字节与同包Linux相同，整段673字节差异保留。eMMC tbl参数/重定位对应1379段；尾部未完整解释，无独立AP启动原件。授权及16要求不变，无设备/root/guest。')
ev = dict(readme=REL + '/README.md', verification=REL + '/verification-receipt.json',
          WBI=REL + '/WBI-layout-audit.json', kernel=REL + '/kernel-image-correspondence.json',
          emmc=REL + '/emmc-handoff-proof.json', scope=REL + '/implementation-review.json',
          web_review=REL + '/web-source-review.json', original_or_guest_execution=False, root_or_device_operations=0)
new['latest_stage_evidence']['stage203_WBI_layout_and_early_memory'] = ev
new['recovery_WBI_and_early_memory'] = {**ev, 'metadata_checks':1399,
    'resume64_matches_shipped_kernel':True, 'whole_kernel_identity_proven':False,
    'trailer_fully_interpreted':False, 'independent_AP_boot0_recovered':False,
    'same_body_boot0_p1_or_independent_restore_proven':False}
new['next_safe_offline_actions'] = [
    '195仅主机root01的原具体问题待答；不将继续视为批准，不创建/启动作业、不重问。该对照也不能证明USB或救砖。',
    '公开WBI声明范围和Linux恢复来源已核清；不要反复泛扫同一批模式/日志或将eMMC交接区称为启动备份。',
    '后续研究应直接回答尚缺的原机boot0/p1来源、独立进入和逆写方式；若没有可新增的公开证据或相应设备授权，应明确停在此边界。保留16项全部要求和真实1080p29.97 HEVC主录/长录验收。']
for key in ['authorization', 'requirements', 'prepared_first_device_trial', 'research_priority', 'current_native_owner_channel_candidate', 'prepared_root_host_trial']:
    assert new[key] == old[key], key
assert not new['goal_complete'] and not new['persistent_write_release']
after = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
with (H / 'goal-status-after.json').open('xb') as f:
    f.write(after)
index = R / 'README.md'
ib = index.read_bytes()
with (H / 'readme-rebased-before.md').open('xb') as f:
    f.write(ib)
marker = '## 相机与固件研究\n'
entry = '- [2026-10-29 FX3 WBI恢复范围与早期启动原件边界](<' + REL + '/README.md>)：既有1399段按参考源码和原件复核；Linux恢复入口64字节吻合，eMMC交接区已绑定；未取得独立AP boot0，尾部完整保留。195待答，无设备/root/guest动作。'
text = ib.decode()
assert text.count(marker) == 1 and entry not in text
ia = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
with (H / 'readme-after.md').open('xb') as f:
    f.write(ia)
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
put('final-receipt.json', dict(schema='fx3-stage203-WBI-layout-v1', created_utc=now,
    previous_manifest_sha256=PREV, previous_members_reverified=61, files=members,
    member_count=len(members), mutable_heads_not_manifest_members=True,
    goal_before_sha256=sha256(before).hexdigest(), goal_after_sha256=sha256(after).hexdigest(),
    host01_bundle_sha256_unchanged=HOST, new_approval_granted=False,
    original_or_guest_execution=False, root_or_device_operations=0,
    native_goal_observed='active', native_goal_status_changed_by_assistant=False,
    goal_complete=False, persistent_write_release=False))
print(json.dumps(dict(sealed_manifest_sha256=digest(H / 'final-receipt.json'), members=len(members),
    WBI_records=1399, requirements_unchanged=16, all_authorizations_unchanged=True,
    device_operations=0, goal_complete=False, persistent_write_release=False)))
