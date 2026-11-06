#!/usr/bin/env python3
"""Rebuild read-only FX3 AP/CP completion evidence; no guest/firmware execution.

Run in the existing Capstone venv. Optional arguments: ap:VA:HEX_LENGTH or
cp:VA:HEX_LENGTH only print disassembly and never write a proof.
"""
from pathlib import Path
import hashlib
import io
import json
import plistlib
import struct
import subprocess
import sys
from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = Path(__file__).resolve().parent
EXPECTED_OUT = ROOT / 'work/fx3-vm-20261101/lead-claude/audits/boot-deferred-0119-0328-digital'
PATHS = {
    'ap': ROOT / 'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so',
    'cp': ROOT / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin',
}
SHA = {
    'ap': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'cp': 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
}


def volume_check():
    p = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert p['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert OUT == EXPECTED_OUT


volume_check()
DATA = {k: p.read_bytes() for k, p in PATHS.items()}
ELF = ELFFile(io.BytesIO(DATA['ap']))


def read(k, a, n):
    if k == 'cp':
        assert 0x108000 <= a and a + n <= 0x108000 + len(DATA[k])
        return DATA[k][a - 0x108000:a - 0x108000 + n]
    for s in ELF.iter_segments():
        if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= a and a + n <= s['p_vaddr'] + s['p_filesz']:
            o = s['p_offset'] + a - s['p_vaddr']
            return DATA[k][o:o + n]
    raise ValueError((k, hex(a), n))


def dis(k, a, n):
    c = Cs(CS_ARCH_ARM, CS_MODE_THUMB) if k == 'cp' else Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    c.skipdata = True  # Literal pools/TBB entries remain data, not control-flow proof.
    return [{'va': hex(i.address), 'bytes': i.bytes.hex(),
             'instruction': (i.mnemonic + ' ' + i.op_str).rstrip()}
            for i in c.disasm(read(k, a, n), a)]


def word(a):
    return struct.unpack('<I', read('cp', a, 4))[0]


def header(command, status):
    return struct.pack('<4HI', 0x200d, command, 12, 0x8001, status)


def original_enum_flags():
    """Interpret only the six bounded original A64 switch arms, not firmware."""
    values = []
    table = read('ap', 0x3963654, 6)
    for enum, off in enumerate(table):
        target = 0x2dec094 + struct.unpack('b', bytes([off]))[0] * 4
        flags = [0, 0, 0]
        pc = target
        w0 = None
        for _ in range(8):
            if pc == 0x2dec0b0:
                break
            ins = dis('ap', pc, 4)[0]['instruction']
            if ins == 'mov w0, #1':
                w0 = 1
            elif ins.startswith('strb w0, [x29, #0x'):
                slot = int(ins.split('#0x')[1].split(']')[0], 16) - 0x58
                assert slot in (0, 1, 2) and w0 == 1
                flags[slot] = w0
            elif ins.startswith('b #0x'):
                pc = int(ins.split('#')[1], 16)
                continue
            else:
                raise AssertionError((enum, hex(pc), ins))
            pc += 4
        else:
            raise AssertionError('switch did not converge')
        values.append({'enum': enum, 'switch_target': hex(target),
                       'hrev_vrev_osdrev': flags,
                       'request': (struct.pack('<4H', 0x200d, 0x119, 28, 0x8001)
                                   + bytes(flags) + bytes(17)).hex()})
    assert [x['hrev_vrev_osdrev'] for x in values] == [
        [0, 0, 0], [0, 1, 1], [1, 1, 0], [0, 1, 0], [1, 0, 1], [0, 0, 1]]
    return values


def software_contract_checks():
    """Finite software-profile illustrations; not a runtime hook or CP execution."""
    receipts = []
    # State commit is an actual action; no sound bytes or playback are consumed.
    for path in (0, 1, 3):
        state = {'profile': 'silent-no-playback', 'path': None, 'playback_enabled': False}
        request = struct.pack('<4H2B', 0x200d, 0x328, 10, 0x8001, path, 0)
        state['path'] = request[8] & 7
        reply = header(0x1328, 0x580000)
        receipts.append({'case': 'ADF path shadow committed', 'request': request.hex(),
                         'state': state, 'reply': reply.hex()})
    # Ready service with sensor unavailable: original 4c8dbe -> 4c8e00 branch.
    req = struct.pack('<6I', 3, 0, 0, 0, 0, 0)
    state = {'service_state': 2, 'sensor_enabled': False, 'requested_notify': True,
             'samples_emitted': 0}
    receipts.append({'case': 'digital no-sensor callback result', 'request': req.hex(),
                     'state': state, 'reply': req.hex(), 'status_offset': 16,
                     'metadata': 'reply to this request source; separate allocated payload; never reuse CP pointers'})
    # In software, a real consumer installs the transform before completion.
    for flags in ((0, 0), (1, 0), (0, 1), (1, 1)):
        def transform(x, y):
            return (639 - x if flags[0] else x, 479 - y if flags[1] else y)
        corners = [(0, 0), (639, 0), (0, 479), (639, 479), (123, 321)]
        assert all(transform(*transform(x, y)) == (x, y) for x, y in corners)
        receipts.append({'case': 'coordinate transform/inverse', 'hrev_vrev': flags,
                         'sample_pairs': [[list(p), list(transform(*p))] for p in corners]})
    queue = [{'source': 'request-source', 'orientation': [0, 0, 0]}]
    state = {'geometry': [640, 480], 'orientation': None, 'generation': 0, 'reply': None}
    before = state.copy()
    assert state['reply'] is None  # Merely enqueuing never completes 0119.
    item = queue.pop(0)
    state.update(orientation=item['orientation'], generation=1)
    state['reply'] = header(0x1119, 0).hex()
    assert not queue and state['orientation'] == [0, 0, 0]
    receipts.append({'case': 'identity orientation consumed, then complete', 'before_consume': before,
                     'after_consume': state, 'physical_panel': False})
    return {'not_runtime_implemented': True, 'cases': receipts,
            'reject_before_success': [
                'wrong endpoint/header/length/padding or unbound original source',
                'duplicate or concurrently reused request lease',
                'ADF path outside boot subset 0/1/3 or playback enabled',
                'digital op !=3 or body not 20 zero bytes; service not ready; fabricated sample data',
                '0119 not exact captured boot packet; nonzero modes without implemented plane/input transforms',
                '0119 consumer absent, transform generation not committed, surface/input mapping inconsistent',
                'allocation/send failure: preserve pending transaction and release only owned reply',
            ]}


BLOCKS = {
    'ap': [
        (0x2b67a70, 0x110), (0x2b67ce4, 0xac), (0x2b67e14, 0xac),
        (0x2b5fc68, 0x98), (0x2b680a0, 0x150), (0x2b66ba8, 0x60), (0x2b63bf0, 0x3c),
        (0x2dee6f0, 0xd8), (0x2df2f60, 0xf4), (0x2dec02c, 0x100),
        (0x2de70a8, 0x278), (0x2de4574, 0x170), (0x2dcb9c0, 0x48),
    ],
    'cp': [
        (0x1b1a8c, 0x82), (0x1853bc, 0x88), (0x185860, 0x48), (0x5ad926, 0x82),
        (0x1858e4, 0x86), (0x18580c, 0x3e), (0x1adbd4, 0x112), (0x5ca218, 0x52),
        (0x4c8908, 0xcc), (0x4c8ee0, 0x28), (0x145330, 0x34), (0x145410, 0x20),
        (0x1454a6, 0x14), (0x4c8da4, 0x96), (0x4c8e60, 0x68),
        (0x49ef00, 0x10a), (0xa874e2, 0x2c), (0x49f368, 0x230),
        (0x49f4e8, 0x22), (0xa878ca, 0x14), (0xa878de, 0x40),
        (0x4a4f9c, 0xa4), (0x4a5c30, 0x52), (0x4a5d72, 0x28), (0x4a5ec2, 0x3e),
        (0x4a6018, 0x74), (0x4a613a, 0x1c), (0x4a61d4, 0x52), (0xa89f96, 0x68),
        (0x1b3e74, 0x2de), (0x5f48ee, 0xa0), (0x1e8298, 0x68), (0x1e80f4, 0x10c),
        (0x606b16, 0x14), (0x606d92, 0x14), (0x5f4ccc, 0x68),
        (0x606ff4, 0x40), (0x606f5c, 0x28), (0x5f0fae, 0x4e), (0x5bbaa4, 0xea), (0x1aef1c, 0x90),
        (0x1e8d40, 0xe8), (0x610db4, 0x150), (0x1e1ccc, 0x5c),
        (0x607232, 0xb4), (0x6072e6, 0xc6), (0x6073b8, 0x74), (0x60742c, 0x22a),
        (0x60f8ae, 0x30), (0x1e0848, 0x164), (0x1e54e0, 0x94),
        (0x60cc44, 0x56), (0x60daa2, 0xa4), (0x60db68, 0x3e), (0x1aeca0, 0x6c),
    ],
}

CHECKS = [
    ('cp', 0x1b1ac4, 'and r5, r0, #7'),
    ('cp', 0x1853c4, 'subw r0, r0, #0x201'),
    ('cp', 0x1853f6, 'b.w #0x185860'),
    ('cp', 0x18588e, 'bl #0x5ad926'),
    ('cp', 0x5ad938, 'beq #0x5ad990'),
    ('cp', 0x5ad990, 'movw r0, #0xe002'),
    ('cp', 0x5ad99e, 'str r4, [r5]'),
    ('cp', 0x185896, 'movw r1, #0xe002'),
    ('cp', 0x18589e, 'bl #0x1858e4'),
    ('cp', 0x1858f6, 'movw r0, #0x8202'),
    ('cp', 0x18591a, 'str r4, [sp, #0x1a4]'),
    ('cp', 0x1adc8a, 'mov.w r2, #0x580000'),
    ('cp', 0x5ca258, 'str r5, [sp, #0xc]'),
    ('cp', 0x4c8988, 'bl #0x49ef00'),
    ('cp', 0x4c8eee, 'bl #0x145330'),
    ('cp', 0x14535c, 'bl #0x4c8da4'),
    ('cp', 0x4c8db8, 'cmp r0, #2'),
    ('cp', 0x4c8dbe, 'cbz r0, #0x4c8e00'),
    ('cp', 0x4c8e00, 'movs r4, #0'),
    ('cp', 0x4c8dd6, 'bl #0x4c8e60'),
    ('cp', 0x1454a6, 'str.w r5, [r8, #0x10]'),
    ('cp', 0x49ef80, 'strd r4, r8, [sl, #0x14]'),
    ('cp', 0xa874f6, 'ldrd r2, r1, [r5, #0x14]'),
    ('cp', 0xa874fe, 'blx r2'),
    ('cp', 0xa87506, 'movs r0, #0'),
    ('cp', 0x49f4f4, 'blx r3'),
    ('cp', 0x4a5026, 'bl #0xa878d8'),
    ('cp', 0x4a5ee8, 'bl #0xa878ca'),
    ('cp', 0x4a6030, 'blx #0x540320'),
    ('cp', 0x4a6084, 'bl #0x49f908'),
    ('cp', 0x4a6078, 'bl #0xa89f96'),
    ('cp', 0x5f4946, 'movt r0, #0xf02e'),
    ('cp', 0x5f497c, 'bl #0x1e8298'),
    ('cp', 0x1e81aa, 'bl #0x611858'),
    ('cp', 0x607004, 'movt r1, #0x9059'),
    ('cp', 0x606f76, 'b.w #0x1e8cc0'),
    ('cp', 0x5f0fd4, 'str r4, [r6, #8]'),
    ('cp', 0x1e8de8, 'bl #0x610db4'),
    ('cp', 0x610e00, 'blx r3'),
    ('cp', 0x1e1cf4, 'ldr r3, [r0, #0x14]'),
    ('cp', 0x607238, 'movw r0, #0xf02e'),
    ('cp', 0x6072d8, 'bl #0x6073b8'),
    ('cp', 0x607356, 'bl #0x6073b8'),
    ('cp', 0x607542, 'blx r2'),
    ('cp', 0x607622, 'bl #0x1e0848'),
    ('cp', 0x60763a, 'bl #0x1e54e0'),
    ('cp', 0x607644, 'movs r6, #5'),  # NE condition belongs to preceding IT.
    ('cp', 0x607648, 'bl #0x6073b8'),
    ('cp', 0x6073e0, 'movw r0, #0x1101'),
    ('cp', 0x6073fa, 'str r6, [sp, #0x10]'),
    ('cp', 0x1aecb6, 'movs r6, #0'),  # EQ condition belongs to preceding IT.
    ('cp', 0x1aecd8, 'movw r0, #0x1119'),
    ('ap', 0x2dee798, 'bl #0x2de70a8'),
    ('ap', 0x2b67aa8, 'cbnz w0, #0x2b67ce4'),
    ('ap', 0x2b67d8c, 'b #0x2b66ba8'),
    ('ap', 0x2b66bbc, 'b #0x2b63bf0'),
    ('ap', 0x2b63c08, 'bl #0x2ebf3b0'),
    ('ap', 0x2df2fbc, 'bl #0x2de70a8'),
    ('ap', 0x2df2fc0, 'ldr w19, [x29, #0x50]'),
    ('ap', 0x2b67b34, 'cbnz w0, #0x2b67e14'),
    ('ap', 0x2b67ebc, 'b #0x2b66ba8'),
    ('ap', 0x2dec0ec, 'bl #0x2de70a8'),
    ('ap', 0x2b5fcbc, 'cbnz w0, #0x2b5fce8'),
    ('ap', 0x2b5fcfc, 'b #0x2b5fcd4'),
]


def reconstruct():
    proof = {'scope': 'Static AP/CP only; no QEMU, device access, original mutations or runtime integration.',
             'address_rule': 'AP ELF VA; CP Thumb VA = file offset +0x108000; bit0 removed for execution.',
             'sources': {}, 'blocks': {}, 'checks': [], 'tables': {}, 'contracts': {}}
    for k, p in PATHS.items():
        h = hashlib.sha256(DATA[k]).hexdigest()
        assert h == SHA[k], (k, h)
        proof['sources'][k] = {'path': str(p.relative_to(ROOT)), 'bytes': len(DATA[k]), 'sha256': h}
    for k, blocks in BLOCKS.items():
        proof['blocks'][k] = {}
        for a, n in blocks:
            ins = dis(k, a, n)
            assert sum(len(bytes.fromhex(i['bytes'])) for i in ins) == n, (k, hex(a), n)
            proof['blocks'][k][hex(a)] = {'raw': read(k, a, n).hex(), 'instructions': ins,
                                         'mixed_literal_or_TBB_data_possible': k == 'cp'}
    for k, a, want in CHECKS:
        got = dis(k, a, 4)[0]
        assert got['instruction'] == want, (k, hex(a), got, want)
        proof['checks'].append({'image': k, **got})
    # CP class address points, exact slots and device command registry binding.
    classes = {
        'AdfSystemSoundPath': (0xb6ff34, [0x5ad91d, 0x5ad91f]),
        'VdfDisplayCmdSetPanelReverse': (0xb7e1f4, [0x5f1775, 0x5f498f, 0x5f1735, 0x5f48ef, 0x5f48ff, 0x5f4911]),
        'DevPanelCmdSetPanelReverse': (0xb80724, [0x5f1775, 0x607657, 0x1e1ccd, 0x607233, 0x607243, 0x60742d]),
    }
    for name, (vt, expected) in classes.items():
        slots = [word(vt + i * 4) for i in range(len(expected))]
        assert slots == expected
        proof['tables'][name] = {'vtable': hex(vt), 'slots': {hex(i * 4): hex(v) for i, v in enumerate(slots)}}
    assert word(0xefedcc) == 0x11cda18
    queue_masks = [list(struct.unpack('<II', read('cp', 0xb81088 + i * 8, 8))) for i in range(5)]
    assert queue_masks[0] == [9, 0x90590819]
    proof['tables']['device_registry'] = {'getter': '0x606b16', 'table': '0xefece4',
        'entry': '0xefedcc', 'object': '0x11cda18', 'installed_vtable': '0xb80724',
        'constructor': '0x606d92..0x606da4', 'ID': '0x2001/0xf02e',
        'common_dispatch': '0x1e1ccc: accessor kind1 ->Activate, kind2 ->Execute',
        'queue_mask_table': '0xb81088', 'queue_masks_and_ids': [[hex(x) for x in row] for row in queue_masks],
        'mask1_destination': '0x90590819', 'controller': '0x010660f0',
        'controller_constructor': '0x606ff4..0x607030; 5f0fd4 stores queue ID atcontroller+8',
        'controller_run': '0x606f5c..0x606f76 passes010660f0 to1e8cc0'}
    adf_tbb = read('cp', 0x1853d0, 14)
    assert 0x1853d0 + 2 * adf_tbb[1] == 0x1853ec
    proof['tables']['ADF_0202_dispatch'] = {'table': '0x1853d0', 'raw': adf_tbb.hex(),
        'index': 'command-0x201', 'case0202': '0x1853ec', 'tailcall': '0x1853f6 ->0x185860'}
    slots = {hex(s): hex(word(0xb8120c + s)) for s in (0xb0, 0xe4, 0x3e8, 0x400, 0x404, 0x40c)}
    assert slots['0x404'] == '0x60f8b5' and slots['0x400'] == '0x60f8af'
    proof['tables']['subsystem_accessor'] = {'vtable': '0xb8120c', 'slots': slots}
    tbb = read('cp', 0x14534e, 8)
    dest = [0x14534e + 2 * x for x in tbb]
    assert dest[3] == dest[4] == 0x14535a
    proof['tables']['digital_dispatch'] = {'table': '0x14534e', 'raw': tbb.hex(),
        'destinations_by_op': [hex(x) for x in dest], 'state_object': '0x01197a48',
        'registration': '0x4c897a..0x4c8988', 'callback': '0x4c8ee0 ->0x145330'}
    proof['tables']['AP_panel_reverse_enum'] = original_enum_flags()
    proof['contracts']['ADF0328'] = {
        'request_subset': [struct.pack('<4H2B', 0x200d, 0x328, 10, 0x8001, p, 0).hex() for p in (0, 1, 3)],
        'old_success': '042002820c00010000000000', 'old_error_e002': '042002820c00010002e00000',
        'AP_success': header(0x1328, 0x580000).hex(), 'AP_error_e002': header(0x1328, 0x58e002).hex(),
        'meaning': 'Accepted system sound path shadow; synchronous path setter, not playback/physical audio completion.',
        'evidence': ['CP185860..1858a6', 'CP5ad926..5ad9a6', 'CP1858e4..185968', 'CP1adc88..1adcde', 'CP5ca218..5ca268'],
    }
    proof['contracts']['digital'] = {
        'request_and_success_reply': struct.pack('<6I', 3, 0, 0, 0, 0, 0).hex(),
        'original_failure2_reply': struct.pack('<6I', 3, 0, 0, 0, 2, 0).hex(),
        'status_offset': 16,
        'meaning': 'Notification control, not a sample; service_state2 + sensor_enabled0 returns0 without sensor request.',
        'route': 'Incoming destination @transport+12, return/source ID @+16; local metadata source @payload-12. Nonzero return route invokes synchronous callback, copies modified payload back before freeing local message; shared transport transaction signals completion.',
        'callback_does_not_allocate_reply': True,
        'evidence': ['CP4c8da4..4c8e38', 'CP1454a6', 'CP49ef00', 'CPa874e2', 'CP49f368', 'CP4a5c30..4a608c', 'CP4a614c..4a6222'],
        'AP_caveat': 'AP2df2fc0 reads INPUT+16, zero, not reply+16; still waits for24B first. Failure2 in reply alone is ignored by this wrapper.',
    }
    proof['contracts']['VDF0119'] = {
        'old_success': '012001110c00010000000000',
        'AP_success': header(0x1119, 0).hex(),
        'AP_error1': header(0x1119, 0x590001).hex(),
        'AP_error5': header(0x1119, 0x590005).hex(),
        'meaning': 'Display command queues f02e; device dispatcher applies reverse state/driver control then emits1101. Not just receipt of119.',
        'statuses': {'0': 'normal device completion or superseded command cleanup',
                     '1': 'bad device payload mode byte4', '5': 'nonzero reverse/infra operation aggregate'},
        'original_hardware_boundary': 'Device frame counter stage16 must progress; active path calls60cc44->a5df3a and infrastructure60daa2->a878ca. CP completion is after synchronous return of these operations; no separate physical LCD-scanout or IMU event is checked here.',
        'model': 'Only exact captured enum0 initially: enqueue retained source+payload, consume insoftware, install orientation000 and identity surface/input generation, then one1119/status0. Nonzero modes require all visible-plane and inverse-input transforms, including osdRev semantics; absent support reject.',
        'evidence': ['CP5f491c..5f4986', 'CP607242..607654', 'CP1e54e0..1e5572', 'CP1aeca0..1aed0a', 'AP2dec02c..2dec128'],
    }
    proof['AP_failure'] = {
        'ADF0328': '0x58e002 ->local0x7b; nonzero ->2b67ce4 ->2b66ba8 fatal path',
        'digital': 'local nonzero ->2b67e14 ->2b66ba8 fatal; reply.status2 alone not observed due AP input-slot read',
        'VDF0119': 'nonzero converted status ->2b5fce8 logs, then2b5fcd4 epilogue; originalworker naturally completes. Missingreply hangs worker and later single-handle barrier.',
    }
    proof['software_contract'] = software_contract_checks()
    proof['unproven'] = [
        'No current-run full0328/0119 packet/source or sequence+304 value captured here; enum0 identity is proven, bootdefault0 is not.',
        'No runtime implementation, guest reply consumption, surface/input observation, bootnotify, menu or real device acceptance.',
        'Physical audio output, DAC routing completion, LCD scanout/rotation and IMU samples intentionally not implemented by software profile.',
        'Original low-level hardware driver internals belowa5df3a and exact frame-event producer are not emulated; static command-consumer/status path is bound.',
        'NonzeroosdRev application to independent originalplanes remains outside minimal identity-only whitelist; cannot silently collapse to frameflip.',
        'AP digital input-slot status bug is recorded, not used to fabricate successful data or omit completion.',
    ]
    proof['external_sources'] = [
        {'url': 'https://www.capstone-engine.org/lang_python.html', 'checked': '2026-11-01', 'scope': 'API usage only'},
        {'url': 'https://github.com/ARM-software/abi-aa/blob/2025Q1/aapcs64/aapcs64.rst', 'checked': '2026-11-01', 'scope': 'A64 register/argument ABI only'},
    ]
    volume_check()
    (OUT / 'boot-deferred-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'result': 'PASS', 'instruction_checks': len(CHECKS),
                      'blocks': sum(len(x) for x in BLOCKS.values()),
                      'AP_orientation_enums': 6, 'software_cases': len(proof['software_contract']['cases']),
                      'guest_or_device_execution': False}, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for spec in sys.argv[1:]:
            k, a, n = spec.split(':')
            for r in dis(k, int(a, 16), int(n, 16)):
                print(r['va'], r['instruction'])
    else:
        reconstruct()
