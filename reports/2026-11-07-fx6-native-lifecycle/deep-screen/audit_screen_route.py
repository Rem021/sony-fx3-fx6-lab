#!/usr/bin/env python3
"""Read-only, SHA-pinned FX6 native screen-route audit. Standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

EXPECTED = 'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'


def audit(path):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED:
        raise ValueError('FX6 SHA mismatch: this audit does not infer addresses for another build')
    header = struct.unpack_from('<HHIQQQIHHHHHH', data, 16)
    loads = []
    for i in range(header[9]):
        p = struct.unpack_from('<IIQQQQQQ', data, header[4]+i*header[8])
        if p[0] == 1:
            loads.append(p)

    def offset(addr):
        for p in loads:
            if p[3] <= addr < p[3]+p[5]:
                return p[2]+addr-p[3]
        raise ValueError(f'VMA {addr:#x} is not file-backed')

    def u32(addr):
        return struct.unpack_from('<I', data, offset(addr))[0]

    def u64(addr):
        return struct.unpack_from('<Q', data, offset(addr))[0]

    def string(addr):
        a = offset(addr)
        return data[a:data.index(b'\0', a, a+512)].decode('ascii')

    def check_call(pc, target):
        w = u32(pc)
        if w & 0xfc000000 != 0x94000000:
            raise ValueError(f'{pc:#x}: expected BL')
        imm = w & 0x3ffffff
        if imm & 0x2000000:
            imm -= 0x4000000
        if pc+imm*4 != target:
            raise ValueError(f'{pc:#x}: call target mismatch')
        return {'pc': hex(pc), 'target': hex(target)}

    def check_name_xref(pc, expected_name):
        adrp, add = u32(pc), u32(pc+8)
        if adrp & 0x9f00001f != 0x90000002 or add & 0xffc003ff != 0x91000042:
            raise ValueError('Expected ADRP x2 / ADD x2,x2,#imm')
        imm = ((adrp >> 29) & 3) | (((adrp >> 5) & 0x7ffff) << 2)
        if imm & 0x100000:
            imm -= 0x200000
        target = (pc & ~4095)+(imm << 12)+((add >> 10) & 0xfff)
        name = string(target)
        if not name.startswith(expected_name):
            raise ValueError(f'{pc:#x}: unexpected diagnostic name')
        return {'diagnostic_adrp': hex(pc), 'name_vma': hex(target), 'name': name}

    rel = {}
    for i in range(header[11]):
        s = struct.unpack_from('<IIQQQQIIQQ', data, header[5]+i*header[10])
        if s[1] == 4:
            for at in range(s[4], s[4]+s[5], s[9]):
                a, info, addend = struct.unpack_from('<QQq', data, at)
                if info & 0xffffffff == 1027:
                    rel[a] = addend
    registry = 0x293bed8
    if rel.get(0x2ee2100) != registry:
        raise ValueError('Registry GOT relocation mismatch')
    screens = []
    for sid, name, pf, cf, ctor, op, name_pc in [
        (2, 'Shooting', 0xdd3fa4, 0xdb2524, 0xdd3df8, 0xfb2f88, 0xfb2fb8),
        (10, 'Big6 HOME', 0xde1244, 0xdb2f28, 0xde10f4, 0xf2dec0, 0xf2def0),
        (15, 'Menu layer 1', 0xdd75a4, 0xdb3584, 0xdd7470, 0xf5dce0, 0xf5dd10),
    ]:
        row = registry+sid*0x38
        if rel.get(row) != pf or rel.get(row+8) != cf or u32(row+0x20) != sid:
            raise ValueError(f'{name}: registry row mismatch')
        if u32(op) != 0xa9bb7bfd:  # stp x29,x30,[sp,#-0x50]!
            raise ValueError(f'{name}: open_screen prologue mismatch')
        if u32(op+0x1c) != 0x7109541f:  # cmp w0,#0x255
            raise ValueError(f'{name}: invalid-screen sentinel check mismatch')
        screens.append({'name': name, 'screen_id': sid, 'row_vma': hex(row),
            'presenter_factory': hex(pf), 'controller_factory': hex(cf),
            'presenter_constructor': hex(ctor), 'controller_open_request': hex(op),
            'descriptor_words_at_row_0x10': [hex(u32(row+i)) for i in range(0x10,0x38,4)],
            **check_name_xref(name_pc, 'void procam_')})
    calls = [check_call(pc, t) for pc,t in [
        (0xc0b1f8,0xdf92cc), (0xc0b520,0xc0b12c), (0xc0b528,0xc0a69c),
        (0xc0a6cc,0xc09da0), (0xc09e0c,0xde31ac),
        (0xc09e48,0xb173c0), (0xc0b484,0xb19290), (0xc0b4d4,0xb188c0),
        (0xdf690c,0xde3584), (0xdf6930,0xde34fc),
        (0xde1264,0xde10f4), (0xdd4010,0xdd3df8), (0xdd75c4,0xdd7470),
    ]]
    diagnostics = [check_name_xref(pc, prefix) for pc,prefix in [
        (0xdf6734,'void presenter_controller_manager::open_screen_ii'),
        (0xdf7964,'void presenter_controller_manager::open_screen_internal'),
        (0x1009548,'void rep_boot_controller::open_screen'),
        (0x1009c94,'bool rep_boot_controller::process_MODEL_POWER_ON_COMP'),
    ]]
    if rel.get(0x2d2ad38) != 0x1009be0:
        raise ValueError('Boot completion handler function-pointer binding mismatch')
    if rel.get(0x2ee7e38) != 0xc091d0:
        raise ValueError('GRM trigger callback binding mismatch')
    if u32(0xdf9204) != 0x52804aa0 or u32(0xdf9214) != 0xb81f8e60 or u32(0xdf921c) != 0x29067fa0:
        raise ValueError('Initial screen request/sentinel instruction mismatch')
    return {'input': {'path': str(path), 'bytes': len(data), 'sha256': digest},
        'invalid_screen_sentinel': {'hex': '0x255', 'decimal': 597,
            'home_cmp_vma': '0xf2dedc', 'home_cmp_instruction_word': '0x7109541f'},
        'manager_initial_screen_request': {'hex': ['0x255','0x0','0x255'],
            'decimal': [597,0,597], 'mov_vma': '0xdf9204', 'mov_instruction_word': '0x52804aa0'},
        'registry': {'vma': hex(registry), 'got': '0x2ee2100', 'stride': '0x38'},
        'screens': screens, 'direct_call_edges_verified': calls,
        'diagnostic_bindings': diagnostics,
        'native_entry_points': {'app_ctor': '0xc0b12c', 'app_run': '0xc0a69c',
            'app_init': '0xc09da0', 'manager_offset_in_app': '0xa40',
            'manager_ctor': '0xdf92cc', 'manager_initialize': '0xde31ac',
            'grm_trigger_register_call': '0xc09e48', 'grm_trigger_callback': '0xc091d0',
            'manager_open_internal': '0xdf790c', 'manager_open_ii': '0xdf6680',
            'boot_power_on_complete_handler': '0x1009be0'},
        'boundary': 'Static control flow only. No VM, screen opening, frame output, or event delivery proved.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('appfw', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.appfw), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
