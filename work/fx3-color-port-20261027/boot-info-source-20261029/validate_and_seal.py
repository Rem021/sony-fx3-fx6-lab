#!/usr/bin/env python3
"""Independently verify original sources/metadata and seal this stage once."""
import datetime
import fcntl
import hashlib
import json
import mmap
import os
import plistlib
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TASK = HERE.parent
PROJECT = HERE.parents[2]
FW = PROJECT / 'work/sony-firmware-20261024'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    final = HERE / 'final-receipt.json'
    assert not final.exists()
    vol = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert vol['VolumeUUID'] == UUID and vol['MountPoint'] == '/Volumes/KAFU2T'
    prior = TASK / 'cetus-sender-20261029/final-receipt.json'
    assert sha(prior.read_bytes()) == '06d69bb7fadd9f0c193d04a9cbbc77981e669ca12995d1d8c932765aa7a373eb'
    old = json.loads(prior.read_text())
    assert len(old['files']) == 28
    for row in old['files']:
        b = (prior.parent / row['path']).read_bytes()
        assert len(b) == row['bytes'] and sha(b) == row['sha256'], row['path']
    review = read('boot-info-source-review.json')
    sources = {}
    for row in review['sources']:
        b = Path(row['path']).read_bytes()
        assert len(b) == row['bytes'] and sha(b) == row['sha256']
        sources[Path(row['path']).name] = b
    own = review['other_owner_inventory']
    assert sha(Path(own['path']).read_bytes()) == own['sha256']
    reader_path = FW / 'stage2/extraction/read_filesystems.py'
    assert sha(reader_path.read_bytes()) == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    image = FW / 'stage2/extraction/nflasha8.img'
    assert sha(image.read_bytes()) == '3c751e784fe6790a4b455990d7c6e144c33cf51c643cf3bf9523f8a3bd5a6a2b'
    sys.path.insert(0, str(reader_path.parent))
    from read_filesystems import FAT16
    fs = FAT16(image)
    for name in ['DGU.bin', 'MIS.bin']:
        entry = next(x for x in fs.walk() if x['path'] == '/' + name)
        assert fs.data(entry['cluster'], entry['size']) == sources[name]
    ref = read('public-layout-reference.json')
    text = (HERE / ref['saved_source']).read_bytes()
    assert len(text) == ref['bytes'] == 1826
    assert sha(text) == ref['sha256'] == '9385eb4dbc4c2ff05c8cd87cc9c18f3d7ddf6e2798ff445dabfec1d3a4b98484'
    assert ref['commit'] == 'eed29146304bb08576711a5e702a42c27df2cd0d'
    facts = ref['metadata_only_facts']
    assert facts['information_prefix_bytes'] == 0x800 and facts['prefix_target_base'] == '0xfe040000'
    scan = read('FDAT-EXBL-candidate-scan.json')
    h = hashlib.sha256()
    with Path(scan['FDAT_source']).open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            h.update(block)
        assert f.tell() == scan['FDAT_bytes'] == 808704512
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            offsets = []
            pos = 0
            while (at := mm.find(b'EXBL', pos)) >= 0:
                offsets.append(at)
                pos = at + 1
            assert offsets == [0x2faf06ff]
            row = scan['candidates'][0]
            assert sha(mm[offsets[0]:offsets[0] + 0x800]) == row['candidate_prefix_sha256']
    assert h.hexdigest() == scan['FDAT_sha256'] == '694c4e9ea53bce6785521078bcb5728068e6ef3da8f0f052ff5ce23b1cb2b768'
    assert scan['plain_magic_candidates'] == 1 and scan['bounded_plausible_candidates'] == 0
    assert scan['current_CP_pformat_field_matches'] == 0
    nor = sources['loader_nor.bin']
    assert nor[0x166fe:0x16704] == b'\0EXBL\0'
    c = review['candidate_classification']
    assert int(c['outer_member_start'], 16) + int(c['inner_member_data_offset'], 16) + int(c['NOR_file_offset'], 16) == offsets[0]
    assert len(review['source_fragments']) == 6
    for row in review['source_fragments']:
        data = nor if row['source'] == 'NOR' else sources['DGU.bin']
        base = 0xfe049000 if row['source'] == 'NOR' else 0xfe040800
        lo, hi = int(row['VA'], 16), int(row['end_exclusive'], 16)
        assert hi - lo == row['bytes'] and sha(data[lo - base:hi - base]) == row['original_bytes_sha256']
        assert (HERE / row['listing']).stat().st_size > 0
    mis = sources['MIS.bin']
    assert mis[:8] == b'MIS_HEAD' and struct.unpack_from('<I', mis, 8)[0] == len(mis)
    count = struct.unpack_from('<H', mis, 0x12)[0]
    declared_base = struct.unpack_from('<I', mis, 0xc)[0]
    assert count == review['original_MIS']['reader_count'] == 3
    for n, row in enumerate(review['original_MIS']['scripts']):
        off = struct.unpack_from('<I', mis, 0x14 + n * 4)[0]
        assert off == int(row['offset'], 16)
        assert declared_base + off == int(row['original_callback_argument'], 16)
        assert mis[off:off + 32].hex() == row['first32_hex']
    probes = read('boot-info-prefix-results.json')
    strict = probes['strict_original_boot_caller']
    explicit = probes['explicit_original_MIS_reader_prefix']
    assert strict['boundary'] == dict(reason='unmapped_external_state', PC='0xfe0587b0', address='0xfe040090', bytes=4)
    assert explicit['boundary'] == dict(reason='before_original_diagnostic_call', PC='0xfe0561b4', caller_return='0xfe055dd8')
    assert explicit['original_return_samples'] == [dict(PC='0xfe055d44', original_comparison_return='0x0')]
    assert [strict['original_instructions'], explicit['original_instructions']] == [11, 99]
    for row in [strict, explicit]:
        assert row['nonstack_writes'] == 0 and not row['boot_information_supplied'] and not row['DGU_entry_executed']
        assert not row['diagnostic_or_other_function_return_replaced']
    assert probes['device_actions'] == probes['hardware_CPU_operations_executed'] == 0
    validation = dict(status='PASS_SCOPED_ORIGINAL_EXBL_AND_MIS_SOURCE_BOUNDARIES',
        previous_sealed_files_verified=28, original_FDAT_bytes_rehashed_and_searched=808704512,
        exact_plain_EXBL_candidates=1, EXBL_candidate_proved_original_comparison_string=True,
        valid_FX3_EXBL_prefix_obtained=False, separately_compressed_or_encrypted_absence_proved=False,
        original_FAT12_DGU_MIS_independently_recovered_equal=True, original_MIS_table_entries=3,
        original_static_windows=6, bounded_original_NOR_cases=2, strict_boot_table_unresolved=True,
        original_MIS_header_recognized_under_explicit_input=True, DGU_executed=False,
        physical_RAM_chip_or_RAW_or_ISP_obtained=False, other_owner_files_written=False,
        native_Sony_programs_executed=0, CPU_maintenance_or_device_actions=0,
        modified_firmware_produced=False, flashable_package_produced=False, goal_complete=False)
    (HERE / 'validation-results.json').write_text(json.dumps(validation, indent=2) + '\n')
    audit = dict(previous_turn='Progress: scoped Cetus sender and original CPAPP-B block-read boundaries;28 sealed files reverified.',
        current_turn='Progress: EXBL block format located in a pinned metadata-only maintainer reference; unique whole-FDAT plaintext match proven to be original comparison string. FX3 original reader establishes three MIS parameter entries, independently checked in original FAT12, with strict missing-table stop and original MIS-header recognition. No true boot or ISP acceptance inferred.',
        same_impasse_repeated_consecutive_goal_turns=0, persistent_goal_status='active', goal_complete=False,
        next_step='Trace original DGU consumption of the three MIS parameter blocks and actual boot-info production format. Keep full donor/ISP, RAW/MAIN binding, modified-package admission, normal boot and independent recovery open. Never manufacture boot data or operate another owner device/backend.')
    (HERE / 'continuation-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    delta = ('\n- [2026-10-29 FX3 EXBL引导信息与MIS原读取格式](<work/fx3-color-port-20261027/boot-info-source-20261029/README.md>)：完整FDAT唯一明文EXBL证实为原比较字符串；原NOR确认MIS三项参数表，两组前缀区分缺失引导表与独立头识别。未取得真实信息块／DDR初始化／ISP或可刷包，无设备动作。\n').encode()
    with (PROJECT / 'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        before = f.read()
        assert delta not in before
        f.seek(0, os.SEEK_END)
        f.write(delta)
        f.flush()
        os.fsync(f.fileno())
        f.seek(0)
        after = f.read()
        assert after == before + delta
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    (HERE / 'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before), before_sha256=sha(before),
        prefix_unchanged=True, append_bytes=len(delta), append_sha256=sha(delta), after_sha256=sha(after)), indent=2) + '\n')
    files = []
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p == final or '__pycache__' in p.parts:
            continue
        b = p.read_bytes()
        files.append(dict(path=str(p.relative_to(HERE)), bytes=len(b), sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        stage=HERE.name, volume_uuid=UUID, files=files, validation=validation,
        persistent_goal_status='active', goal_complete=False, device_actions=0,
        flashable_package_produced=False), indent=2) + '\n')
    print(json.dumps(dict(sealed_files=len(files), receipt_sha256=sha(final.read_bytes()), validation=validation)))


if __name__ == '__main__':
    main()
