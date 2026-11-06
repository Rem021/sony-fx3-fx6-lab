#!/usr/bin/env python3
"""Pin original boot metadata consumers and the MIS table reader; static only."""
import hashlib
import io
import json
import struct
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
PROJECT = HERE.parents[2]
FW = PROJECT / 'work/sony-firmware-20261024'
BASE = 0xfe049000
NOR_PIN = '4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
DGU_PIN = '39eeb6d572a060149194463507800ed66b866a20dceb8ed49b01a04eb6fb2ba7'
MIS_PIN = '4cd3e9bc3a0a4aec4793bff77e7ca4dccdba8637212cd632cdc5ecbe550daf98'


def digest(b):
    return hashlib.sha256(b).hexdigest()


def source(path, pin):
    b = path.read_bytes()
    assert digest(b) == pin, str(path)
    return b, dict(path=str(path), bytes=len(b), sha256=pin)


def main():
    out = HERE / 'boot-info-source-review.json'
    assert not out.exists()
    nor, nr = source(TASK / 'config-producer-20261029/original-files/loader_nor.bin', NOR_PIN)
    other = FW / 'stage198-AP-CP-loaders-and-partition-selection'
    dgu, dr = source(other / 'originals/DGU.bin', DGU_PIN)
    mis, mr = source(other / 'originals/MIS.bin', MIS_PIN)
    inventory = (other / 'source-inventory.json').read_bytes()
    inv = json.loads(inventory)
    for name, data, pin in [('DGU.bin', dgu, DGU_PIN), ('MIS.bin', mis, MIS_PIN)]:
        row = next(x for x in inv['components'] if x['path_in_image'] == '/' + name)
        assert row['source_hash_verified'] and row['bytes'] == len(data) and row['sha256'] == pin
    fmt, fr = source(TASK / 'config-producer-20261029/original-files/pformat_config.txt',
                     '21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece')
    manifest = json.loads((FW / 'fx3-7.02-offline-manifest.json').read_text())
    member = next(x for x in manifest['tar_members'] if x['name'] == '0750_nor_loader/loader_nor.tar')
    start = manifest['firmware_tar_offset'] + member['data_offset_in_tar']
    with (FW / 'fx3-7.02-decrypted.fdat').open('rb') as f:
        f.seek(start)
        blob = f.read(member['size'])
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:') as t:
        leaf = t.getmember('loader_nor.bin')
        assert t.extractfile(leaf).read() == nor
        assert t.extractfile('pformat_config.txt').read() == fmt
        inner_offset = leaf.offset_data
    off = nor.index(b'EXBL')
    assert nor.count(b'EXBL') == 1 and off == 0x166ff
    assert nor[off - 1] == 0 and nor[off + 4] == 0
    scan = json.loads((HERE / 'FDAT-EXBL-candidate-scan.json').read_text())
    assert scan['plain_magic_candidates'] == 1
    assert int(scan['candidates'][0]['FDAT_offset'], 16) == start + inner_offset + off
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    listing_dir = HERE / 'listings'
    listing_dir.mkdir(exist_ok=False)
    windows = []
    for name, data, base, lo, hi in [
        ('NOR-boot-table-getters', nor, BASE, 0xfe058794, 0xfe0588a4),
        ('NOR-EXBL-check', nor, BASE, 0xfe0588a4, 0xfe0588e4),
        ('NOR-MIS-header-reader', nor, BASE, 0xfe055d14, 0xfe055ec8),
        ('NOR-DGU-MIS-caller', nor, BASE, 0xfe056024, 0xfe056050),
        ('DGU-entry-static-only', dgu, 0xfe040800, 0xfe040800, 0xfe0408a0),
        ('DGU-parser-prefix-static-only', dgu, 0xfe040800, 0xfe04536c, 0xfe045448),
    ]:
        raw = data[lo - base:hi - base]
        lines = [f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in md.disasm(raw, lo)]
        target = listing_dir / (name + '.txt')
        target.write_text('\n'.join(lines) + '\n')
        windows.append(dict(source='NOR' if data is nor else 'DGU', VA=hex(lo), end_exclusive=hex(hi),
                            bytes=len(raw), original_bytes_sha256=digest(raw),
                            listing=str(target.relative_to(HERE)), instruction_listing_is_static=True))
    assert mis[:8] == b'MIS_HEAD'
    size, declared_base = struct.unpack_from('<II', mis, 8)
    count = struct.unpack_from('<H', mis, 0x12)[0]
    offsets = list(struct.unpack_from('<' + 'I' * count, mis, 0x14))
    assert size == len(mis) == 119296 and declared_base == 0xfe080000
    assert count == 3 and offsets == [0xa00, 0xc200, 0x13200]
    scripts = []
    for index, offset in enumerate(offsets):
        assert 0 <= offset < len(mis)
        scripts.append(dict(index=index, offset=hex(offset), original_callback_argument=hex((declared_base + offset) & 0xffffffff),
                            first32_hex=mis[offset:offset + 32].hex(),
                            initial_u16=hex(struct.unpack_from('<H', mis, offset)[0])))
    assert struct.unpack_from('<Q', dgu, 0x98)[0] == 0xfe0440c8
    version = mis[0x123:mis.index(b'\0', 0x123)].decode('ascii')
    result = dict(
        sources=[nr, dr, mr, fr], other_owner_inventory=dict(path=str(other / 'source-inventory.json'), sha256=digest(inventory),
            use='Read-only hash/source binding. Its unguarded scripts are not imported or run.'),
        candidate_classification=dict(FDAT_offset=hex(start + inner_offset + off), outer_member_start=hex(start),
            inner_member_data_offset=hex(inner_offset), NOR_file_offset=hex(off), NOR_VA=hex(BASE + off),
            exact_NUL_delimited_string='EXBL', kind='Original code comparison string, not an EXBL information block'),
        original_EXBL_check=dict(entry='0xfe0588a4', compare_call='0xfe0588bc', compare_helper='0xfe04b364',
            comparison='Bounded string comparison; both EXBL and MIS_HEAD have no NUL within their compared lengths.',
            source_address='0xfe040000', comparison_string_VA='0xfe05f6ff', bytes=4, failure_return=-409),
        original_boot_getter=dict(entry='0xfe058794', field_base='0xfe040050', stride='0x40',
            index2_address='0xfe040090', index3_address='0xfe0400d0', index5_address='0xfe040150',
            actual_values_available=False),
        original_DGU_MIS_caller=dict(entry='0xfe056024', DGU_getter_index=2, MIS_getter_index=3,
            function_tailcall='0xfe05604c', target_reader='0xfe055d14', reader_argument0='0x10',
            real_boot_table_or_target_values_supplied=False),
        original_MIS_reader=dict(entry='0xfe055d14', magic_compare_bytes=8, magic_compare_call='0xfe055d40',
            declared_base_u32_offset='0xc', count_u16_offset='0x12', table_u32_offset='0x14', table_stride=4,
            count_read_PC='0xfe055ddc', table_load_PC='0xfe055e20', base_load_PC='0xfe055e1c',
            base_plus_offset_PC='0xfe055e30', indirect_DGU_call_PC='0xfe055e40',
            first_argument='Original mode argument preserved in w20', second_argument='32-bit declared base plus selected u32 table entry'),
        original_MIS=dict(magic='MIS_HEAD', file_bytes=len(mis), size_word_u32_8=size, declared_base=hex(declared_base),
            reader_count=count, scripts=scripts, version_text_at_0x123=version,
            word_0x10_not_named_as_version=True, individual_script_lengths_not_established=True),
        original_DGU_entry=dict(configured_load='0xfe040800', original_literal_at='0xfe040898',
            literal_target='0xfe0440c8', branch_target='0xfe04536c',
            CPU_maintenance_present=['0xfe040840 dsb sy', '0xfe040844 ic ialluis', '0xfe040848 dsb sy', '0xfe04084c isb'],
            entry_executed=False),
        source_fragments=windows,
        interpretation=dict(complete_FX3_EXBL_prefix_obtained=False, public_parser_exact_model_compatibility_proved=False,
            original_MIS_table_format_and_three_parameters_located=True, RAM_chip_capacity_or_timing_compatibility_proved=False,
            actual_DDR_initialization_executed=False, CMOS_RAW_or_ISP_recovered=False, flashable_package_produced=False),
        scope='Static original-byte review only. DGU/MIS are original CP payload components; their source path is not an operational device reading. Header offsets follow the FX3 NOR reader itself. No BootROM, keys, decryption, manufactured EXBL block, original DGU execution, CPU registers/cache/TLB, device or native Sony operation.')
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(candidate=result['candidate_classification'], MIS=result['original_MIS'],
                          static_windows=len(windows), original_DGU_executed=False)))


if __name__ == '__main__':
    main()
