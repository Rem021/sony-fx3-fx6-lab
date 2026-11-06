#!/usr/bin/env python3
"""Bounded static index of FX6 AV look/DMA callers. No guest or device execution."""
import hashlib
import json
import pathlib
import struct

from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs

ROOT = pathlib.Path(__file__).resolve().parent
AV = ROOT.parents[2] / 'fat-files/nflasha3/av-cam.bin'
PIN = '56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'
BASE = 0xffffffc001000000
CODE_SCAN_END = 0x370000
TARGETS = [0x2a7978, 0x2a650c, 0x2a7374, 0x2a7ba4, 0x29b308, 0x29b290]
REGIONS = {
    'event_handoff': (0x2a72b8, 0x2a7334),
    'event_provider_thunk': (0x2ede0, 0x2edf4),
    'dispatch': (0x2a7374, 0x2a7458),
    'look_caller': (0x2a7458, 0x2a74f4),
    'lookup': (0x2a650c, 0x2a659c),
    'mode_update': (0x29b290, 0x29b308),
    'mode_provider_thunk': (0x2efd4, 0x2efe8),
    'mode_flag': (0x29b308, 0x29b334),
    'ip_register_base': (0x297460, 0x297474),
    'dma_builder_inputs': (0x2a7978, 0x2a79b4),
    'other_callers': (0x2a7574, 0x2a7758),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def h(n):
    return hex(n)


def sign(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def direct_calls(data, target):
    out = []
    for offset in range(0, CODE_SCAN_END, 4):
        word = struct.unpack_from('<I', data, offset)[0]
        kind = word >> 26
        if kind not in (0b000101, 0b100101):
            continue
        dest = offset + (sign(word & 0x3ffffff, 26) << 2)
        if dest == target:
            out.append({'file_offset': h(offset), 'va': h(BASE + offset),
                        'kind': 'BL' if kind == 0b100101 else 'B',
                        'word_le': data[offset:offset+4].hex()})
    return out


def absolute_refs(data, target):
    # Exact 64-bit pointer and simple in-order ADR/ADRP+ADD materializations only.
    ptr = struct.pack('<Q', BASE + target)
    qwords = []
    start = 0
    while (offset := data.find(ptr, start)) >= 0:
        qwords.append(h(offset))
        start = offset + 1
    pc_relative = []
    for offset in range(0, CODE_SCAN_END - 4, 4):
        word = struct.unpack_from('<I', data, offset)[0]
        if word & 0x9f000000 == 0x10000000:  # ADR
            imm = sign((((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3), 21)
            if offset + imm == target:
                pc_relative.append({'file_offset': h(offset), 'kind': 'ADR'})
        if word & 0x9f000000 != 0x90000000:  # ADRP
            continue
        imm = sign((((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3), 21) << 12
        page = (offset & ~0xfff) + imm
        nxt = struct.unpack_from('<I', data, offset + 4)[0]
        if nxt & 0x7f000000 != 0x11000000:  # ADD immediate, 32/64 bit
            continue
        rd = word & 31
        if (nxt & 31) != rd or ((nxt >> 5) & 31) != rd:
            continue
        shift = 12 if (nxt >> 22) & 1 else 0
        value = page + (((nxt >> 10) & 0xfff) << shift)
        if value == target:
            pc_relative.append({'file_offset': h(offset), 'kind': 'ADRP+ADD'})
    return {'exact_qword_offsets': qwords, 'simple_pc_relative_refs': pc_relative,
            'scan_scope': f'whole file qword; aligned 0x0-{CODE_SCAN_END:x} ADR and adjacent ADRP+ADD'}


def disassemble(data, start, end, md):
    return [{'file_offset': h(ins.address - BASE), 'va': h(ins.address),
             'bytes_le': ins.bytes.hex(), 'text': f'{ins.mnemonic} {ins.op_str}'.strip()}
            for ins in md.disasm(data[start:end], BASE + start)]


def main():
    data = AV.read_bytes()
    assert digest(data) == PIN and len(data) == 12939512
    assert struct.unpack_from('<Q', data, 0)[0] == BASE + 0x58
    assert data[8:12] == b'ORIL'
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    calls = {h(t): direct_calls(data, t) for t in TARGETS}
    assert [int(x['file_offset'], 16) for x in calls[h(0x2a7978)]] == [
        0x2a74e4, 0x2a75ac, 0x2a7600, 0x2a7690, 0x2a7748]
    assert [int(x['file_offset'], 16) for x in calls[h(0x2a7374)]] == [0x2a731c]
    assert [int(x['file_offset'], 16) for x in calls[h(0x29b290)]] == [0x29d48c, 0x2a729c]
    refs = absolute_refs(data, 0x2a7978)
    assert not refs['exact_qword_offsets'] and not refs['simple_pc_relative_refs']
    jump = [struct.unpack_from('<Q', data, 0x370198 + 8*i)[0] - BASE for i in range(6)]
    assert jump == [0x2a73cc, 0x2a73d8, 0x2a73e4, 0x2a73f0, 0x2a73fc, 0x2a7408]
    assert struct.unpack_from('<I', data, 0x370098)[0] == 22
    assert struct.unpack_from('<Q', data, 0x370098 + 8)[0] == BASE + 0xaa2ca0
    assert struct.unpack_from('<I', data, 0x370098 + 16)[0] == 70
    assert data[0xb45884] == 0 and struct.unpack_from('<I', data, 0xbb0bfc)[0] == 2
    result = {
        'source': {'path': str(AV), 'sha256': PIN, 'size': len(data), 'format': 'ORIL AArch64 flat image',
                   'base': h(BASE), 'map_rule': 'VA = base + file offset; header qword at 0x0 = base + 0x58'},
        'code_scan_end_exclusive': h(CODE_SCAN_END), 'direct_branch_index': calls,
        'dma_builder_address_refs': refs,
        'dispatch_jump_table': {'file_offset': '0x370198', 'sha256': digest(data[0x370198:0x3701c8]),
                                'targets': [h(x) for x in jump]},
        'look22_static_row': {'file_offset': '0x370098', 'key': 22, 'descriptors': '0xaa2ca0', 'count': 70,
                              'sha256': digest(data[0x370098:0x3700b8])},
        'alternate_look_table': {'file_offset': '0xb81ae8', 'first_key': 31,
                                 'first_descriptor_offset': h(struct.unpack_from('<Q', data, 0xb81af0)[0]-BASE),
                                 'first_count': struct.unpack_from('<I', data, 0xb81af8)[0],
                                 'static_count_returned_by_0x29b320': 24},
        'snapshot_state_not_runtime': {'look_override_flag_at_0xb45884': data[0xb45884],
                                       'mode_word_at_0xbb0bfc': struct.unpack_from('<I', data, 0xbb0bfc)[0]},
        'runtime_provider_edges': [
            {'caller': '0x2a72d0', 'thunk': '0x2ede0', 'provider_slot': '0x3c0',
             'incoming_value': 'event pointer written through x1=sp+8; must observe return and pointed event'},
            {'caller': '0x29b2a4', 'thunk': '0x2efd4', 'provider_slot': '0x4c0',
             'incoming_value': '4-byte word written through x1=sp+0xc; must observe return and word'},
        ],
        'regions': {k: {'start': h(a), 'end_exclusive': h(z), 'sha256': digest(data[a:z]),
                        'instructions': disassemble(data, a, z, md)} for k, (a, z) in REGIONS.items()},
        'finding_scope': 'direct branches in aligned code window and exact/simple address refs only; no claim about indirect dynamic calls',
    }
    (ROOT/'static-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'source_sha256': PIN, 'direct_dma_calls': [x['file_offset'] for x in calls[h(0x2a7978)]],
                      'event_dispatch_call': calls[h(0x2a7374)][0]['file_offset'],
                      'jump_targets': [h(x) for x in jump], 'address_refs': refs}))


if __name__ == '__main__':
    main()
