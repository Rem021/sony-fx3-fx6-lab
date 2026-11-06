#!/usr/bin/env python3
"""Read-only FX3 enum2 audit. No ARM/guest execution or runtime modifications.

Only the adjacent proof is written (unless --check or a disassembly query).
Run with the existing Capstone venv from the project root. Query: ap:VA:LEN,
cp:VA:LEN, obj:VA:LEN (hex), with no output files.
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
VM = ROOT / 'work/fx3-vm-20261101/menu-repair-01'
OUT = Path(__file__).resolve().parent
EXPECTED_OUT = ROOT / 'work/fx3-vm-20261101/lead-claude/audits/panel-reverse-enum2'
P = {
    'ap': VM / 'original-uipc/ap-projection/regular-files/usr/lib/appFw.so',
    'obj': VM / 'original-uipc/ap-projection/regular-files/usr/lib/libObj.so',
    'cp': ROOT / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin',
    'capture': VM / 'runtime/ap80b2-frozen-orientation.bin',
    'capture_json': VM / 'runtime/ap80b2-orientation-capture.json',
    'a7c2_reference': VM / 'success-cases/display-reuse/supplemental-source/runtime/analysis/device-models/vdf-device.c',
}
PINS = {
    'ap': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'obj': 'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
    'cp': 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
    'capture': '19e2db159542cfaba7ca1209be58106580765dc4b960301a3b7cc040f76935e6',
    'capture_json': 'b4b292fe417be751ce63f3cdf156cb97ac691250dc0ad24144ab9d394b0fdbfe',
    'a7c2_reference': '578dd4e3ca46d272fd60a361da6d53c78af772cf30c82ea590c6578becc6613e',
}
REQUEST = bytes.fromhex('0d2019011c0001800101000000000000000000000000000000000000')


def volume_check():
    p = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert p['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert OUT == EXPECTED_OUT


volume_check()
DATA = {k: p.read_bytes() for k, p in P.items()}
ELF = {k: ELFFile(io.BytesIO(DATA[k])) for k in ('ap', 'obj')}


def read(k, a, n):
    if k == 'cp':
        off = a - 0x108000
        assert off >= 0 and off + n <= len(DATA[k])
        return DATA[k][off:off+n]
    for s in ELF[k].iter_segments():
        if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= a and a+n <= s['p_vaddr']+s['p_filesz']:
            off = s['p_offset']+a-s['p_vaddr']
            return DATA[k][off:off+n]
    raise ValueError((k, hex(a), n))


def dis(k, a, n):
    c = Cs(CS_ARCH_ARM, CS_MODE_THUMB) if k == 'cp' else Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    c.skipdata = True
    return [{'va': hex(i.address), 'bytes': i.bytes.hex(),
             'instruction': (i.mnemonic+' '+i.op_str).strip()}
            for i in c.disasm(read(k, a, n), a)]


def u32(k, a):
    return struct.unpack('<I', read(k, a, 4))[0]


def reply(status):
    return struct.pack('<4HI', 0x200d, 0x1119, 12, 0x8001, status)


BLOCKS = {
 'ap': [
    (0x2c20ce8, 0x40), (0x2c210ec, 0x28), (0x2932154, 0x28),
    (0x2823890, 0x898), (0x2811bf8, 0x50), (0x29810d0, 0xa0),
    (0x2b6719c, 0x54), (0x2eabfd0, 0x94), (0x2eac0c0, 0xc),
    (0x2b5fc68, 0x98), (0x2dec02c, 0x100), (0x2de70a8, 0x278),
    (0x2de4574, 0x2a0), (0x2b680a0, 0x150), (0x2dcb9c0, 0x48),
    (0x16f06d4, 0xb0), (0x16f0ca8, 0x18),
 ],
 'cp': [
    (0x1b3e74, 0x2de), (0x5f48ee, 0xa0), (0x1e8298, 0x68),
    (0x606d92, 0x14), (0x606ff4, 0x40), (0x1e1ccc, 0x5c),
    (0x607232, 0xb4), (0x6072e6, 0xc6), (0x6073b8, 0x74), (0x60742c, 0x22a),
    (0x60f8ae, 0x30), (0x1e0848, 0x164), (0x1e54e0, 0x94),
    (0x60cc44, 0x56), (0xa5df3a, 0x3e), (0xa62d32, 0x278),
    (0x60daa2, 0x104), (0x5dea6a, 0x40), (0x5deb9e, 0x10),
    (0x5dec2e, 0x50), (0x5dc14a, 0xa), (0x1c3394, 0x44),
    (0x1c34cc, 0x8), (0x1c35ba, 0x1a), (0x5ded9c, 0xe),
    (0x1c37bc, 0xe0), (0x1c4098, 0x148), (0x1c77dc, 0xae),
    (0x5e6058, 0x3e), (0x1c7aee, 0x22), (0x5e2f34, 0x12a),
    (0x1adbd4, 0x112), (0x1aeca0, 0x6c), (0x1aef1c, 0x90),
 ],
 'obj': [
    (0xd2a3c, 0xc0), (0xd53bc, 0x1d8), (0xd6a7c, 0xe4),
    (0xd4124, 0x54), (0xcb640, 0xac),
 ],
}

# Expected Capstone strings are pinned to the unchanged original inputs.
CHECKS = [
 ('ap', 0x2c20d14, 'str x0, [x19]'),
 ('ap', 0x2c210f8, 'bl #0x2932154'),
 ('ap', 0x2c21100, 'str w0, [x19, #0x304]'),
 ('ap', 0x293215c, 'add x0, x0, #0x10, lsl #12'),
 ('ap', 0x2932160, 'add x0, x0, #0x1e4'),
 ('ap', 0x2823ad8, 'add x0, x0, #0x1ba'),
 ('ap', 0x2823aec, 'mov w1, #2'),
 ('ap', 0x2823b20, 'mov w20, #2'),
 ('ap', 0x2823ba4, 'mov w0, #0x243'),
 ('ap', 0x2811c2c, 'str w0, [x1]'),
 ('ap', 0x2811c34, 'str w0, [x1]'),
 ('ap', 0x2b671bc, 'ldr w0, [x19, #0x304]'),
 ('ap', 0x2b671cc, 'bl #0x2ddfb74'),
 ('ap', 0x2eabff4, 'stp wzr, wzr, [x29, #0x58]'),
 ('ap', 0x2eac044, 'bl #0x2eace78'),
 ('ap', 0x2eac0c4, 'stp w0, w0, [x29, #0x58]'),
 ('ap', 0x2b5fca4, 'ldr w0, [x21, #0x304]'),
 ('ap', 0x2b5fcbc, 'cbnz w0, #0x2b5fce8'),
 ('ap', 0x2b5fcfc, 'b #0x2b5fcd4'),
 ('ap', 0x2de47dc, 'mov w19, #0x6a'),
 ('ap', 0x2de47e4, 'mov w19, #0x6e'),
 ('ap', 0x16f06dc, 'bl #0x2932154'),
 ('ap', 0x16f06f0, 'cmp w21, #2'),
 ('cp', 0x60751e, 'ldrb r1, [r0]'),
 ('cp', 0x607528, 'ldrb r0, [r0, #1]'),
 ('cp', 0x607542, 'blx r2'),
 ('cp', 0x607548, 'ldrb.w r8, [r8, #2]'),
 ('cp', 0x607616, 'mov r2, r8'),
 ('cp', 0x607622, 'bl #0x1e0848'),
 ('cp', 0x60762e, 'mov r2, r8'),
 ('cp', 0x607638, 'mov r1, fp'),
 ('cp', 0x60763a, 'bl #0x1e54e0'),
 ('cp', 0x607642, 'it ne'),
 ('cp', 0x607644, 'movs r6, #5'),  # standalone lacks preceding IT context
 ('cp', 0x607648, 'bl #0x6073b8'),
 ('cp', 0x1e5506, 'ldrd r1, r0, [r0, #4]'),
 ('cp', 0x1e5514, 'it eq'),
 ('cp', 0x1e5516, 'movs r2, #2'),
 ('cp', 0x1e551c, 'it eq'),
 ('cp', 0x1e551e, 'movs r0, #3'),
 ('cp', 0x1e5534, 'bl #0x60daa2'),
 ('cp', 0x1e08e6, 'str r5, [sp, #0x34]'),
 ('cp', 0x1e0948, 'bl #0x60cc44'),
 ('cp', 0x60cc78, 'bl #0xa5df3a'),
 ('cp', 0xa5df5a, 'bl #0xa62d32'),
 ('cp', 0xa62eae, 'ldr r0, [r4, #0x28]'),
 ('cp', 0x60daf0, 'strb.w r0, [sp, #0x1c]'),
 ('cp', 0x60db78, 'bl #0xa878ca'),
 ('cp', 0x5deba6, 'str.w r1, [r4, #0xdc]'),
 ('cp', 0x5dec44, 'movt r2, #0x27d'),
 ('cp', 0x5dec7a, 'b.w #0x49ef00'),
 ('cp', 0x5dc150, 'b.w #0x1c3394'),
 ('cp', 0x1c35c0, 'ldrb.w r0, [sb, #0xc]'),
 ('cp', 0x1c35c4, 'strb.w r0, [r8, #0x74]'),
 ('cp', 0x5deda6, 'b.w #0x1c37bc'),
 ('cp', 0x1c37fc, 'strb.w r5, [sp, #0x14]'),
 ('cp', 0x1c382c, 'strb.w r5, [sp, #0x11]'),
 ('cp', 0x1c388e, 'bl #0x1c4098'),
 ('cp', 0x1c41d0, 'bl #0x1c77dc'),
 ('cp', 0x1c784a, 'bl #0x5e6058'),
 ('cp', 0x1c785e, 'bl #0x5e6058'),
 ('cp', 0x5e6074, 'strb r1, [r3]'),
 ('cp', 0x1c7af4, 'bl #0x5e6078'),
 ('obj', 0xd2a94, 'strb w21, [x19, #0x51]'),
 ('obj', 0xd2a9c, 'strb w20, [x19, #0x50]'),
 ('obj', 0xd5548, 'ldr w0, [x19, #8]'),
 ('obj', 0xd555c, 'ldr w0, [x19, #0xc]'),
 ('obj', 0xd5590, 'bl #0x57830'),
 ('obj', 0xd6ac4, 'ldrb w0, [x19, #0x50]'),
 ('obj', 0xd6ad0, 'sub w25, w0, w25'),
 ('obj', 0xd6ad4, 'ldrb w0, [x19, #0x51]'),
 ('obj', 0xd6ae0, 'sub w20, w0, w20'),
 ('obj', 0xd6afc, 'sub w25, w1, #1'),
 ('obj', 0xd6b0c, 'sub w20, w0, #1'),
]


def orientation_enums():
    result = []
    for enum, off in enumerate(read('ap', 0x3963654, 6)):
        target = 0x2dec094 + struct.unpack('b', bytes([off]))[0]*4
        flags, pc, w0 = [0, 0, 0], target, None
        for _ in range(8):
            if pc == 0x2dec0b0:
                break
            ins = dis('ap', pc, 4)[0]['instruction']
            if ins == 'mov w0, #1':
                w0 = 1
            elif ins.startswith('strb w0, [x29, #0x'):
                slot = int(ins.split('#0x')[1].split(']')[0], 16)-0x58
                assert slot in (0, 1, 2) and w0 == 1
                flags[slot] = w0
            elif ins.startswith('b #0x'):
                pc = int(ins.split('#')[1], 16)
                continue
            else:
                raise AssertionError((enum, hex(pc), ins))
            pc += 4
        else:
            raise AssertionError('switch failed to converge')
        result.append({'enum': enum, 'target': hex(target), 'h_v_osd': flags,
                       'request': (struct.pack('<4H', 0x200d, 0x119, 28, 0x8001)+bytes(flags)+bytes(17)).hex()})
    assert result[2]['request'] == REQUEST.hex()
    return result


def tp_enum_map():
    # The original A64 switch only has two nonzero arms and a common zero arm.
    table = read('ap', 0x399ecb0, 5)
    out = []
    for enum, off in enumerate(table):
        a = 0x2eac018 + struct.unpack('b', bytes([off]))[0]*4
        assert a in (0x2eac018, 0x2eac020, 0x2eac0c0)
        xy = {0x2eac018: (1, 0), 0x2eac020: (0, 0), 0x2eac0c0: (1, 1)}[a]
        out.append({'enum': enum, 'target': hex(a), 'x_y_direction': xy,
                    'request': struct.pack('<4I', 0, 16, *xy).hex()})
    assert out[2]['x_y_direction'] == (0, 0)
    return out


def software_examples():
    """Executable proposed config-level contract, never original CP execution.

    Pixel-grid choice is explicitly defined by this software example; it does
    not establish Sony panel mounting, exact OSD scanout, or raw sensor units.
    """
    q = [{'source': 0x81cf61c0, 'request': REQUEST, 'generation': 1}]
    state = {'applied': None, 'reply': None}
    pending = dict(state)
    item = q.pop(0)  # independent f02e-equivalent consumer
    state['applied'] = {'generation': item['generation'], 'hrev': 1, 'vrev': 1,
                        'osdRev': 0, 'panel_control': 3,
                        'owner': 'virtual-panel-config', 'buffer_content_modified': False,
                        'frame_policy': 'raw logical export; optional named virtual scan-grid view',
                        'input_policy': 'logical post-InfraTp injection, or original calibrated raw path once'}
    assert state['applied']['panel_control'] == 3
    state['reply'] = reply(0).hex()
    pairs = []
    for x, y in ((0, 0), (639, 479), (123, 321), (639, 0)):
        # Explicit software virtual scan-grid T; not inferred hardware mount.
        dx, dy = 639-x, 479-y
        assert (639-dx, 479-dy) == (x, y)
        # Native calibrated InfraTp: false means max-coordinate - sample,
        # followed by clamp; NOT (max-1)-sample. Here maxX/Y declared 640/480.
        native = (min(639, 640-x), min(479, 480-y))
        pairs.append({'logical': [x, y], 'virtual_scan_grid': [dx, dy],
                      'virtual_scan_grid_inverse': [639-dx, 479-dy],
                      'native_false_false_example_input': [x, y],
                      'native_false_false_example_output': list(native)})
    rejected = 0
    for n in range(len(REQUEST)):
        bad = bytearray(REQUEST)
        bad[n] ^= 1
        assert bytes(bad) != REQUEST
        rejected += 1
    for bad in (REQUEST[:-1], REQUEST+b'\0', b''):
        assert bad != REQUEST
        rejected += 1
    return {'proposed_only': True, 'pending_before_consume': pending,
            'state_after_consume_before_transport_send': state,
            'coordinate_examples': pairs, 'exact_packet_negative_cases': rejected,
            'software_checks_are_not_runtime_or_render_acceptance': True}


def reconstruct():
    sources = {}
    for k, p in P.items():
        digest = hashlib.sha256(DATA[k]).hexdigest()
        if k in PINS:
            assert digest == PINS[k], (k, digest)
        sources[k] = {'path': str(p), 'bytes': len(DATA[k]), 'sha256': digest}
    cap = json.loads(DATA['capture_json'])
    assert DATA['capture'] == REQUEST and cap['full_raw'] == REQUEST.hex()
    assert 'enum=2' in cap['enum_marker'][0] and not cap['identity_reply_enabled']
    blocks = {}
    for k, spans in BLOCKS.items():
        blocks[k] = [{'start': hex(a), 'length': hex(n), 'raw': read(k, a, n).hex(),
                      'instructions': dis(k, a, n),
                      'warning': 'Thumb long ranges may contain literals/TBB bytes; anchors and table targets define control flow.' if k == 'cp' else ''}
                     for a, n in spans]
    checks = []
    for k, a, expected in CHECKS:
        row = dis(k, a, 4)[0]
        assert row['instruction'] == expected, (k, hex(a), row, expected)
        checks.append({'image': k, **row})
    sy = ELF['obj'].get_section_by_name('.dynsym')
    pl = ELF['obj'].get_section_by_name('.plt')
    rel = ELF['obj'].get_section_by_name('.rela.plt')
    plt = {pl['sh_addr']+32+i*16: sy.get_symbol(r['r_info_sym']).name for i, r in enumerate(rel.iter_relocations())}
    assert plt[0x57830] == '_ZN7InfraTp14SetTpDirectionEbb'
    strings = {}
    for k, a in [('ap', 0x37a5cc0), ('ap', 0x379c1ba), ('ap', 0x379c153),
                 ('ap', 0x379c2af), ('ap', 0x379c2dc), ('ap', 0x379c30a),
                 ('obj', 0x1d6ed3), ('obj', 0x1d74b4), ('obj', 0x1d74d8),
                 ('cp', 0xd87811), ('cp', 0xd87828), ('cp', 0xd8783f)]:
        strings[f'{k}:{a:x}'] = read(k, a, 180).split(b'\0')[0].decode('ascii')
    tbb = read('cp', 0x1c34d0, 4)
    assert 0x1c34d0+2*tbb[2] == 0x1c35ba
    masks = [struct.unpack('<II', read('cp', 0xb81088+8*i, 8)) for i in range(5)]
    assert masks[0] == (9, 0x90590819)
    assert u32('cp', 0xb8120c+0x400) == 0x60f8af
    assert u32('cp', 0xb8120c+0x404) == 0x60f8b5
    assert u32('cp', 0xb8120c+0x40c) == 0x60f8d3
    assert struct.unpack('<QQ', read('ap', 0x40a14e0, 16)) == (0x40c0580, 0x243)
    assert struct.unpack('<Q', read('ap', 0x40c0580, 8))[0] == 0x822c718
    ref_lines = DATA['a7c2_reference'].decode().splitlines()
    ref = [{'line': i+1, 'text': s} for i, s in enumerate(ref_lines)
           if 165 <= i+1 <= 226 and any(t in s for t in ('reverse_', 'bytes!=28', 'in[8]', 'in[10]', 'pixels_flipped', 'hardware_driver'))]
    result = {
      'scope': 'FX3 enum2 static audit; captured AP80b2 is a prior runtime receipt, no new guest execution',
      'sources': sources, 'capture': cap, 'instruction_checks': checks, 'blocks': blocks,
      'strings': strings,
      'tables': {
        'orientation': orientation_enums(), 'touch_direction': tp_enum_map(),
        'parameter_binding': {'parameter': '0x243', 'table_entry': '0x40a14e0',
          'binding': '0x40c0580 ->0x822c718', 'current': '0x822c71c', 'next': '0x822c720',
          'getter': '0x2932154', 'snapshot_store': '0x2c21100 ->sequence+0x304',
          'update': '0x2823890 update_params_for_panel_vali_angle_status',
          'enum2_named_branch': 'REVERSE_CLOSE @0x2823acc ->0x2823b20 ->0x2823bbc ->0x2811bf8'},
        'queue_masks': [[hex(x), hex(y)] for x, y in masks],
        'panel_control_callback': {'register': '0x5dec2e..0x5dec7a', 'endpoint': '0x027d0728',
          'callback': '0x5dc14a ->0x1c3394', 'reverse_op': '0x20000002',
          'dispatch_table': '0x1c34d0', 'raw': tbb.hex(), 'target': '0x1c35ba',
          'stored_control': 'context+0x74', 'installed_callback': 'context+0xdc =0x5ded9d',
          'next': '0x5ded9c ->0x1c37bc ->0x1c4098 ->0x1c77dc',
          'orientation_shadow': '0x5e6058 stores control in 0x01438e59 or0x0143902c',
          'later_read': '0x1c7af4 ->0x5e6078',
          'lowest_specific_panel_register_not_proven': True},
        'tp_plt': {'0x57830': plt[0x57830]},
      },
      'completion': {
        'old_status0': '012001110c00010000000000', 'ap_status0': reply(0).hex(),
        'ap_bad_mode1': reply(0x590001).hex(), 'ap_operation_error5': reply(0x590005).hex(),
        'ap_local_status': {'0x00000000': '0', '0x00590001': '0x6a', '0x00590005': '0x6e'},
        'success_order': ['f02e enqueue', 'device consumer scheduling/frame target',
                         'h/v properties saved', 'conditional OSD layout control',
                         'panel infrastructure callback returns', '1101', 'BB translates590000 to0', '1119'],
        'ap_error': 'nonzero converted status logs Failure and returns normally; no reply blocks worker and its parent barrier',
        'status0_caveat': 'Activate cleanup of superseded requests may also complete0; never a physical scanout proof',
      },
      'software_contract': {
        'exact_request_only': REQUEST.hex(), 'source_metadata': '92840747 -> this request original source, captured81cf61c0 is not a global constant',
        'configuration': {'hrev': 1, 'vrev': 1, 'osdRev': 0, 'panel_control': 3},
        'independent_consumer': 'retain source+lease+generation; enqueue f02e-equivalent item; consumer installs and reads back config before exactly one1119/status0',
        'honest_success_level': 'virtual-panel-config control accepted and installed; no hardware driver or physical scanout equivalence',
        'export_domains': {
           'logical-framebuffer': 'export original AP/GPE bytes and original logical coordinates unchanged; attach orientation metadata',
           'virtual-scan-grid': 'explicit software choice mount=identity, compose visible planes then T(x,y)=(W-1-x,H-1-y); inverse=T; osdRev0 adds no OSD-specific reverse',
           'human-facing-physical-panel': 'requires independently proven panel mount/base scan and plane composition; do not guess from enum2'},
        'input_domains': {
           'physical_keys': 'MENU/arrows/ENTER keycodes unchanged; no coordinate transform',
           'logical-post-InfraTp': 'inject UI logical coords; inverse of viewer T exactly once when clicking a virtual-scan-grid view',
           'pre-InfraTp-raw': 'use existing calibration then native false/false maps(maxX-x,maxY-y) with clamp; do not preflip again; raw units/packet contract not recovered here'},
        'transport': 'OSAL allocator/source setter/send; retain request until ownership transfer rule is known; free only owned unsent reply on failure; never forge worker token/notify',
        'alternative': 'if original physical plane/mount equivalence required, leave pending or send original failure590005 and let worker finish naturally; no identity rewrite or forced notify',
        'examples': software_examples(),
      },
      'a7c2_reference': {'lines': ref, 'same': 'state-only virtual panel control, osd0,1119/status0, explicit hardware0/pixels0',
                         'different': 'FX3 whitelist exactly enum2 capture; original VA and TP path rederived; all boolean h/v combinations not authorized by one capture'},
      'unproven': [
        'The actual FX3 physical hinge state, active Backup record, factory default of parameter243, or real-camera universal boot enum2; AP80b2 alone cannot prove them.',
        'The final electrical panel scan direction register/MMIO and fixed panel mounting/base orientation; logical H/V names and control3 are proven, exact human-facing pixels are not.',
        'The complete OSD/YUV scaler/plane blend and active scanout binding; osdRev0 means separate field0, not proof that OSD bypasses all panel reversal.',
        'No global AP redraw requirement or global absence thereof is proven; AP explicitly reads parameter243 for some UI geometry at16f06dc.',
        'Raw touch packet injection format, sensor calibration values/maxima and current TP command consumption remain unverified; native false/false math is proven.',
        'No new virtual consumer implementation/integration,1119 consumption, bootnotify, menu screenshot, input event or physical camera acceptance.',
      ],
      'external_sources': [{'url': 'https://www.capstone-engine.org/lang_python.html',
                            'checked': '2026-11-01', 'scope': 'disassembly API only; Sony semantics are local original VA evidence'}],
      'no_qemu_or_guest_or_device_execution': True,
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    dest = OUT / 'panel-reverse-enum2-proof.json'
    volume_check()
    if '--check' in sys.argv:
        assert dest.read_text() == encoded, 'proof differs'
    else:
        dest.write_text(encoded)
    print(json.dumps({'result': 'PASS', 'instruction_checks': len(checks),
                      'blocks': sum(len(x) for x in BLOCKS.values()),
                      'orientation_enums': 6, 'touch_enums': 5,
                      'negative_packet_cases': result['software_contract']['examples']['exact_packet_negative_cases'],
                      'guest_execution': False, 'check_only': '--check' in sys.argv}))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] != '--check':
        for spec in sys.argv[1:]:
            k, a, n = spec.split(':')
            for r in dis(k, int(a, 16), int(n, 16)):
                print(r['va'], r['instruction'])
    else:
        reconstruct()
