#!/usr/bin/env python3
"""Rebuild the FX3 RM/FRONT static audit; never execute firmware or start QEMU."""
import argparse
import hashlib
import io
import json
import plistlib
import re
import struct
import subprocess
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
VM = ROOT / 'work/fx3-vm-20261101/menu-repair-01'
LIB = VM / 'original-uipc/ap-projection/regular-files/usr/lib'
RUN = VM / 'runtime/runs/ap92media-9e1c3a07'
CP = ROOT / 'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
KMOD = ROOT / 'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha15/kmod/mcmn_drv.ko'
SEED = VM / 'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin'
ARM64 = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
THUMB = Cs(CS_ARCH_ARM, CS_MODE_THUMB)


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Elf:
    def __init__(self, path):
        self.path = Path(path)
        self.b = self.path.read_bytes()
        self.e = ELFFile(io.BytesIO(self.b))
        self.syms = self.e.get_section_by_name('.dynsym') or self.e.get_section_by_name('.symtab')
        self.reloc = {}
        for sec in self.e.iter_sections():
            if sec['sh_type'] != 'SHT_RELA':
                continue
            # Only ET_REL needs section relocations here. DSO code annotations use
            # .rela.plt below; their original data pointers already carry local VAs.
            if self.e['e_type'] != 'ET_REL':
                continue
            sy = self.e.get_section(sec['sh_link'])
            target = self.e.get_section(sec['sh_info']).name if sec['sh_info'] else 'absolute'
            for r in sec.iter_relocations():
                s = sy.get_symbol(r['r_info_sym'])
                name = s.name
                if not name and isinstance(s['st_shndx'], int):
                    name = self.e.get_section(s['st_shndx']).name
                self.reloc[(target, r['r_offset'])] = {
                    'symbol': name, 'symbol_value': hex(s['st_value']),
                    'addend': hex(r['r_addend']), 'type': r['r_info_type']}
        pl = self.e.get_section_by_name('.plt')
        rel = self.e.get_section_by_name('.rela.plt')
        self.plt = {}
        if pl and rel:
            sy = self.e.get_section(rel['sh_link'])
            self.plt = {pl['sh_addr']+32+i*16: sy.get_symbol(r['r_info_sym']).name
                        for i, r in enumerate(rel.iter_relocations())}

    def read(self, a, n, section=None):
        if section:
            b = self.e.get_section_by_name(section).data()[a:a+n]
        else:
            s = next(s for s in self.e.iter_segments() if s['p_type'] == 'PT_LOAD'
                     and s['p_vaddr'] <= a and a+n <= s['p_vaddr']+s['p_filesz'])
            o = s['p_offset']+a-s['p_vaddr']
            b = self.b[o:o+n]
        assert len(b) == n
        return b

    def dis(self, a, n, section=None):
        result = []
        for i in ARM64.disasm(self.read(a, n, section), a):
            row = {'va': hex(i.address), 'bytes': bytes(i.bytes).hex(),
                   'instruction': (i.mnemonic+' '+i.op_str).strip()}
            rel = self.reloc.get((section, i.address))
            if rel:
                row['relocation'] = rel
            if i.mnemonic == 'bl' and i.op_str.startswith('#'):
                symbol = self.plt.get(int(i.op_str[1:], 16))
                if symbol:
                    row['symbol'] = symbol
            if i.mnemonic == 'ldr' and ', #' in i.op_str and '[' not in i.op_str:
                lit = int(i.op_str.split(', #')[1], 0)
                rel = self.reloc.get((section, lit))
                if rel:
                    row['literal_relocation'] = {'location': hex(lit), **rel}
            result.append(row)
        return result


def backup_entries(b):
    addr, cookie, flags, rev, ns, np, start, size, checksum = struct.unpack_from('<III4s5I', b)
    assert cookie == 0xaaaaaaaa and rev == b'BK4\0' and ns <= 1024
    assert start+size <= len(b) and 256+6*(ns+np) <= start
    out = {}
    for sid in range(ns):
        count, index = struct.unpack_from('<HI', b, 256+sid*6)
        assert index+count <= np
        for pid in range(count):
            entry = 256+6*ns+(index+pid)*6
            attr, pointer = struct.unpack_from('<HI', b, entry)
            if pointer == 0xffffffff:
                continue
            n, o = pointer >> 24, pointer & 0xffffff
            if n == 255:
                n = struct.unpack_from('<H', b, o)[0]
                o += 2
            elif n == 0:
                n, capacity = struct.unpack_from('<HH', b, o)
                o += 4
                assert n <= capacity
            assert start <= o and o+n <= start+size
            out[(sid << 16)|pid] = {'attribute': attr, 'offset': hex(o), 'bytes': n,
                                    'entry_offset': hex(entry), 'raw': b[o:o+n].hex()}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    assert ROOT == Path('/Volumes/KAFU2T/AI/Projects/Mac')
    assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/rm-media-service'
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'].upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    proof = {'schema': 'fx3-rm-media-service-readonly-v1',
             'assessment': 'STATIC_PROTOCOL_AUDIT_COMPLETE_WITH_EXPLICIT_RUNTIME_AND_HARDWARE_GAPS',
             'scope': 'Only this directory is written; no QEMU, firmware execution, runtime edits, lock, Git, or camera access.',
             'sources': {}, 'blocks': {}, 'checks': []}

    def source(name, path, pin=None):
        b = Path(path).read_bytes()
        digest = sha(b)
        if pin:
            assert digest == pin, (name, 'source changed', digest)
        proof['sources'][name] = {'path': str(path), 'bytes': len(b), 'sha256': digest}
        return b

    pins = {
        'D': ('libInfraMediaDetect.so', '4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d'),
        'M': ('libInfraMediaMount.so', '33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad'),
        'C': ('libInfraMediaCommon.so', '1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b'),
        'A': ('appFw.so', '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f')}
    images = {}
    for name, (filename, pin) in pins.items():
        source(name, LIB/filename, pin)
        images[name] = Elf(LIB/filename)
    kb = source('K', KMOD, 'da4596fe04a1c932fac6c9b160c031bfb817e85caf3e77c6219d2f013a8d9b22')
    images['K'] = Elf(KMOD)
    cp = source('P', CP, 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba')
    specs = [
        ('rm_sync', 'D', 0xf1e4, 0x154),
        ('get_config', 'D', 0xfd4c, 0xbc),
        ('set_notify_queue', 'D', 0xfe08, 0x7c),
        ('detect_ctor', 'D', 0x10390, 0x174),
        ('detect_init', 'D', 0x1007c, 0x314),
        ('detect_front_callback', 'D', 0xe6dc, 0x218),
        ('detect_thread_init', 'D', 0xe8f4, 0x40c),
        ('detect_parse', 'D', 0x1091c, 0x668),
        ('detect_update', 'D', 0xfb48, 0x204),
        ('detect_start', 'D', 0xf92c, 0x128),
        ('detect_notify', 'D', 0xd40c, 0x184),
        ('detect_notify_adapter', 'D', 0xf8d8, 0x54),
        ('mount', 'M', 0x9c98, 0x2e0),
        ('common_rm_init', 'C', 0x3c7a8, 0x318),
        ('common_rm_getname', 'C', 0x39020, 0x3c),
        ('app_insert_adapter', 'A', 0x2a7a7a4, 0xc4),
        ('app_eject_adapter', 'A', 0x2a7a868, 0x120),
        ('caution_predicate', 'A', 0x1799794, 0x134),
        ('kernel_init', 'K', 0, 0x60, '.init.text'),
        ('kernel_core_init', 'K', 0xd48, 0x20c, '.text'),
        ('kernel_rm_thread', 'K', 0x1000, 0x240, '.text'),
        ('kernel_rm_setnotify', 'K', 0x1258, 0x110, '.text'),
        ('kernel_rm_getport', 'K', 0x1378, 0x298, '.text'),
        ('kernel_rm_init', 'K', 0x16a8, 0xb0, '.text'),
        ('kernel_cmd9', 'K', 0x1918, 0x64, '.text'),
        ('kernel_cmd3', 'K', 0x19e0, 0x18, '.text'),
        ('kernel_uipc_callback', 'K', 0x1a38, 0x80, '.text'),
        ('kernel_uipc_thread', 'K', 0x1ac8, 0x388, '.text'),
        ('kernel_uipc_init', 'K', 0x1e68, 0x90, '.text'),
        ('kernel_backup_config', 'K', 0x10698, 0x178, '.text'),
        ('kernel_pci_config_update', 'K', 0x108b8, 0x68, '.text'),
        ('kernel_config_getptr', 'K', 0x10928, 0x30, '.text'),
        ('kernel_config_build', 'K', 0x10b48, 0x348, '.text')]
    for spec in specs:
        name, key, a, n, *sec = spec
        section = sec[0] if sec else None
        raw = images[key].read(a, n, section)
        proof['blocks'][name] = {'source': key, 'section': section,
                                 'start': hex(a), 'bytes': n, 'sha256': sha(raw),
                                 'instructions': images[key].dis(a, n, section)}
    for name, a, n in [
        ('cp_front_rm_compare', 0xab274e, 0x58),
        ('cp_front_rm_publish_policy', 0xab27a6, 0x102),
        ('cp_front_rm_sender', 0xab28a8, 0xd2),
        ('cp_front_state_get', 0xab485a, 0x18)]:
        raw = cp[a-0x108000:a-0x108000+n]
        proof['blocks'][name] = {'source': 'P', 'section': 'Thumb VA, file offset=VA-0x108000',
                                 'start': hex(a), 'bytes': n, 'sha256': sha(raw),
                                 'instructions': [{'va': hex(i.address), 'bytes': bytes(i.bytes).hex(),
                                                   'instruction': (i.mnemonic+' '+i.op_str).strip()}
                                                  for i in THUMB.disasm(raw, a)]}

    def check(block, a, instruction, symbol=None):
        row = next(r for r in proof['blocks'][block]['instructions'] if r['va'] == hex(a))
        assert row['instruction'] == instruction, (block, row, instruction)
        if symbol:
            assert row.get('symbol', row.get('relocation', {}).get('symbol')) == symbol
        proof['checks'].append({'block': block, 'va': hex(a), 'instruction': instruction,
                                 'symbol': symbol, 'pass': True})

    for row in [
        ('kernel_init', 0x40, 'bl #0x40', 'mcmnd_uipc_init'),
        ('kernel_uipc_init', 0x1ebc, 'mov w0, #0x16e'),
        ('kernel_uipc_init', 0x1ec4, 'movk w0, #0x80d9, lsl #16'),
        ('kernel_uipc_init', 0x1ec8, 'bl #0x1ec8', 'osal_reg_msg_queue_cb'),
        ('kernel_uipc_thread', 0x1cc0, 'blr x1'),
        ('kernel_uipc_thread', 0x1cd8, 'str w21, [x29, #0x84]'),
        ('kernel_uipc_thread', 0x1cfc, 'bl #0x1cfc', 'osal_snd_msg'),
        ('kernel_cmd9', 0x1928, 'mov w0, #1'),
        ('kernel_cmd9', 0x192c, 'bl #0x192c', 'mcmnd_rmcfg_getinfoptr'),
        ('kernel_cmd3', 0x19ec, 'bl #0x19ec', 'mcmnd_core_setosalidformedianotify'),
        ('kernel_rm_thread', 0x1014, 'mov w21, #0x17c'),
        ('kernel_rm_thread', 0x101c, 'movk w21, #0x8028, lsl #16'),
        ('kernel_rm_thread', 0x1134, 'bl #0x1134', 'osal_snd_msg'),
        ('kernel_rm_setnotify', 0x12ac, 'mov w2, #7'),
        ('kernel_rm_setnotify', 0x130c, 'bl #0x130c', 'osal_set_msg_src'),
        ('kernel_rm_setnotify', 0x1318, 'bl #0x1318', 'osal_snd_msg'),
        ('rm_sync', 0xf2a8, 'bl #0x9060', 'osal_rcv_msg_tmo'),
        ('rm_sync', 0xf29c, 'mov w2, #-1'),
        ('rm_sync', 0xf2fc, 'ldr w20, [x19, #0xc]'),
        ('detect_ctor', 0x10498, 'bl #0x9740', 'osal_reg_msg_queue_cb'),
        ('detect_ctor', 0x104a8, 'bl #0x9780', '_ZN24InfraMediaDetectThreadRM23SetOsalIdForMediaNotifyEj'),
        ('detect_ctor', 0x104dc, 'bl #0x9510', '_ZN26InfraMediaDetectThreadBase11StartThreadEPKc'),
        ('detect_front_callback', 0xe868, 'strb w0, [x19, #0x2a0]'),
        ('detect_front_callback', 0xe870, 'bl #0x9540', 'pthread_cond_signal'),
        ('detect_thread_init', 0xe9d0, 'bl #0x90d0', 'pthread_cond_timedwait'),
        ('detect_thread_init', 0xe9d8, 'cmp w0, #0x6e'),
        ('detect_parse', 0x109bc, 'cmp w2, #2'),
        ('detect_parse', 0x10cc0, 'strb w1, [x19, #0x268]'),
        ('detect_parse', 0x10d38, 'bl #0x8dd0', '_ZN24InfraMediaDetectThreadRM6UpdateEv'),
        ('detect_update', 0xfd0c, 'mov w1, #2'),
        ('detect_update', 0xfd10, 'stur w1, [x19, #-4]'),
        ('detect_start', 0xfa00, 'cmp w0, #2'),
        ('detect_start', 0xfa04, 'b.eq #0xfa34'),
        ('cp_front_rm_sender', 0xab28b2, 'movw r8, #0x17c'),
        ('cp_front_rm_sender', 0xab28be, 'movs r2, #7'),
        ('cp_front_rm_sender', 0xab28ca, 'movt r8, #0x8028'),
        ('cp_front_rm_sender', 0xab2904, 'movs r1, #2'),
        ('cp_front_rm_sender', 0xab2906, 'strb r1, [r0]'),
        ('cp_front_rm_sender', 0xab2908, 'movs r1, #0'),
        ('cp_front_rm_sender', 0xab290a, 'strb r1, [r0, #1]'),
        ('cp_front_rm_sender', 0xab290c, 'strb r1, [r0, #2]'),
        ('cp_front_rm_sender', 0xab293a, 'bl #0x49f140')]:
        check(*row)

    k = images['K']
    table = k.read(0x40, 13*24, '.rodata')
    proof['kernel_commands'] = []
    for i in range(13):
        o = 0x40+i*24
        command, = struct.unpack_from('<I', table, i*24)
        minimum, = struct.unpack_from('<I', table, i*24+16)
        handler = k.reloc[('.rodata', o+8)]
        proof['kernel_commands'].append({'table_offset': hex(o), 'command': command,
                                         'minimum_total_bytes': minimum, 'handler': handler})
    assert next(r for r in proof['kernel_commands'] if r['command'] == 9)['handler']['addend'] == '0x1918'
    assert next(r for r in proof['kernel_commands'] if r['command'] == 3)['handler']['addend'] == '0x19e0'
    assert k.reloc[('.text', 0x1ee0)]['addend'] == '0x1ac8'
    assert k.reloc[('.text', 0x1738)]['addend'] == '0x1000'
    assert k.reloc[('.text', 0x1ef0)]['addend'] == '0x1a38'
    jump_maps = []
    for offset, pc in [(0x4d0, 0x10d40), (0x4d8, 0x10dd8)]:
        raw = k.read(offset, 8, '.rodata')
        targets = {str(t): hex(pc+struct.unpack_from('<b', raw, t-1)[0]*4) for t in [1, 2, 4, 8]}
        jump_maps.append({'section_offset': hex(offset), 'raw': raw.hex(), 'branch_base': hex(pc),
                          'media_bit_to_target': targets})
    assert jump_maps[0]['media_bit_to_target'] == {'1': '0x10df8', '2': '0x10de8', '4': '0x10dd8', '8': '0x10d40'}
    assert jump_maps[1]['media_bit_to_target'] == {'1': '0x10e50', '2': '0x10e40', '4': '0x10e30', '8': '0x10e10'}
    proof['kernel_config_jump_tables'] = jump_maps
    proof['original_media_event_names'] = []
    for p in range(0x4171670, 0x41716f0, 16):
        ident, length, pointer = struct.unpack('<IIQ', images['A'].read(p, 16))
        name = images['A'].read(pointer, length).split(b'\0')[0].decode()
        proof['original_media_event_names'].append({'va': hex(p), 'id': hex(ident),
                                                    'name_va': hex(pointer), 'name': name})
    assert [r['id'] for r in proof['original_media_event_names']] == [hex(0x10000+i) for i in range(8)]
    proof['common_rm_path_table'] = []
    for i, pointer in enumerate(struct.unpack('<3Q', images['C'].read(0x71d00, 24))):
        name = images['C'].read(pointer, 12).split(b'\0')[0].decode()
        assert name == '/nondev/rm'+str(i+1)
        proof['common_rm_path_table'].append({'table_va': hex(0x71d00+8*i), 'index': i,
                                               'string_va': hex(pointer), 'path': name})
    pointer_raw = cp[0xd11978-0x108000:0xd1197c-0x108000]
    assert struct.unpack('<I', pointer_raw)[0] == 0xab27a7
    proof['cp_publish_callback_pointer'] = {'va': '0xd11978', 'raw': pointer_raw.hex(),
                                            'thumb_target': '0xab27a6',
                                            'table_record_formal_name': 'unproven'}
    proof['queue_ownership'] = {
        'service': 'AP Linux kernel module mcmn_drv.ko; not a CP RM request queue',
        'static_service_queue': '0x80d9016e', 'register': 'K .text+0x1e68..0x1ec8',
        'callback': 'K .text+0x1a38', 'worker': 'K .text+0x1ac8',
        'thread_name': 'RMCMND-UIPC', 'front_worker': 'K .text+0x1000',
        'front_queue': '0x8028017c', 'front_thread_name': 'RMCMND-RM',
        'cp_sender': 'P 0xab28a8..0xab2978; calls allocation 0x49f80c and send 0x49f140',
        'source_note': 'CP publisher does not explicitly set a source ID here; exact original CP allocator source is not derived. Cached AP replay explicitly sets source=notification destination (K+0x12f0..0x1318).'}

    seed = source('backup_seed', SEED, 'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2')
    ram = source('ap92_backup_ram', RUN/'backup-reserved-ram.bin', '249e2d085c335a052010042cf9f561ebd9d748f33efa38c4c8dc1f1db6e903c9')
    seed_items, ram_items = backup_entries(seed), backup_entries(ram)
    keys = [0xd90141, 0xd9013e, 0xd9013f, 0xd90140, 0xd90142, 0xd90143, 0xd90144, 0xd90145,
            0xd90182, 0xd90183, 0xd90184]
    proof['backup_port_config'] = []
    for key in keys:
        a, b = seed_items[key], ram_items[key]
        assert a['bytes'] == b['bytes'] == 1 and a['raw'] == b['raw']
        proof['backup_port_config'].append({'key': hex(key), **a, 'ap92_same_value': True})
    raw_table = k.read(0x4e0, 8*24, '.rodata')
    rows = []
    for i in range(8):
        _, _, index, media_bit, target, backup = struct.unpack_from('<6I', raw_table, i*24)
        port = int(seed_items[backup]['raw'], 16)
        rows.append({'row_offset': hex(0x4e0+i*24), 'device_index': index, 'media_type_bit': media_bit,
                     'target': hex(target), 'backup_key': hex(backup), 'physical_rm_port': port})
    assert [r['physical_rm_port'] for r in rows] == [1, 2, 3, 0, 2, 3, 0, 0]
    logical = [int(seed_items[x]['raw'], 16) for x in [0xd90182, 0xd90183, 0xd90184]]
    assert logical == [1, 2, 3]
    proof['kernel_backup_table'] = rows

    # Instruction-derived projection of K+0x10b48. This is not native execution.
    # 0x70=one selector word + three 0x24B records. No port-count or card capacity field.
    configs = []
    for view in [0, 1]:
        cfg = bytearray(0x70)
        struct.pack_into('<I', cfg, 0, view)
        for port in range(1, 4):
            record = 4+(port-1)*0x24
            mask = (1 << (port-1)) if not view else sum(1 << i for i, v in enumerate(logical) if v == port)
            struct.pack_into('<II', cfg, record, port-1, mask)
            support = 0
            for r in rows:
                match = r['physical_rm_port']
                if view and match:
                    match = logical[match-1]
                if match != port:
                    continue
                support |= r['media_type_bit']
                offset = {1: 12, 2: 16, 4: 20, 8: 24}[r['media_type_bit']]
                struct.pack_into('<I', cfg, record+offset, int(r['target'], 16))
            struct.pack_into('<I', cfg, record+8, support)
        configs.append(bytes(cfg))
    cfg = configs[1]
    decoded_cfg = [struct.unpack_from('<9I', cfg, 4+i*36) for i in range(3)]
    assert decoded_cfg == [(0, 1, 1, 0x10, 0, 0, 0, 0, 0),
                           (1, 2, 6, 0, 0x20, 0xb0, 0, 0, 0),
                           (2, 4, 6, 0, 0x21, 0xb1, 0, 0, 0)]
    proof['configuration_projection'] = {
        'level': 'B: projection from original instruction control/data flow and frozen Backup; not native execution',
        'source': 'K+0x10698,0x10928,0x10b48..0x10e2c; .rodata+0x4e0',
        'total': 112, 'header_word': 1, 'port_records': 3, 'stride': 36,
        'header_word_is_port_count': False, 'record_words': decoded_cfg, 'payload_hex': cfg.hex(),
        'field_layout': {'+0': 'configuration view selector=1 (physical/logical naming inferred)',
                         '+4+i*36+0': 'zero-based RM record index',
                         '+4+i*36+4': 'physical port bitmask',
                         '+4+i*36+8': 'supported media bitmap: MS=1,MMC=2,PCIe=4,other=8',
                         '+4+i*36+12/16/20/24': 'MS/MMC/PCIe/other target IDs',
                         '+4+i*36+28': 'u16 PCI bus info + u8 device/function + reserved byte',
                         '+4+i*36+32': 'u32 PCI auxiliary info, formal semantic name unproven'},
        'dynamic_limit': 'Last8B of each record are zero immediately after original build; real hardware can update them at K+0x108b8. No original live PCI values captured. Software no-PCI provider keeps zero and does not claim physical PCI identity.'}

    serial = source('L92', RUN/'serial.log', '0fb5e9749828e327ed12639952bfb5923be32c43d6cd83e259feed9ea0135e48')
    lines = serial.decode(errors='replace').split('\n')
    selected = []
    for i, line in enumerate(lines, 1):
        line = line.rstrip('\r')
        if (line.startswith('FX3_MEDIA_') and ('FX3_MEDIA_STACK' not in line)
                or 'Caution [MOUNT_ERR_EXTMEDIA_SLOT1_FOR_AUTO_TRIGGER] appears' in line):
            selected.append({'line': i, 'text': line})
    proof['serial'] = {'line_numbering': 'LF-separated, one-based', 'line_count': len(lines), 'selected': selected}
    assert any('FX3_MEDIA_INIT_WAIT_RETURN' in r['text'] and 'native_rc=110' in r['text'] for r in selected)
    assert not any('FX3_MEDIA_FRONT ' in r['text'] or 'tag=FRONT_FULL_BODY ' in r['text'] for r in selected)
    headers = [r for r in selected if 'tag=RM_ENTRY_HEADER24' in r['text']]
    assert len(headers) == 2
    request_examples = []
    for r in headers:
        raw = bytes.fromhex(re.search(r'raw=([0-9a-f]+)', r['text']).group(1))
        cmd, version, payload, queue, status, tail = struct.unpack('<IHHIIQ', raw)
        assert (version, queue, status, tail) == (1, 0x80af615f, 0, 0)
        assert (cmd, payload) in [(9, 112), (3, 4)]
        request_examples.append({'line': r['line'], 'header_hex': raw.hex(), 'command': cmd,
                                 'version': version, 'payload_bytes': payload, 'reply_queue': hex(queue),
                                 'status': status, 'tail_u64': tail})
    proof['request_examples'] = request_examples
    notification_queue = 0x80af6180
    assert any('tag=RM_RETURN_PAYLOAD' in r['text'] and 'raw=8061af80 ' in r['text'] for r in selected)
    packets = []
    for cmd, payload in [(9, cfg), (3, struct.pack('<I', notification_queue))]:
        header = struct.pack('<IHHIIQ', cmd, 1, len(payload), 0x80af615f, 0, 0)
        packets.append({'command': cmd, 'total_bytes': 24+len(payload), 'reply_hex': (header+payload).hex(),
                         'scope': 'Software-provider fixture using AP92 reply IDs; use current request IDs, never hard-code them in a new run.'})
    proof['reply_fixtures'] = packets
    proof['rm_header'] = {
        'byte_order': 'little', 'header_bytes': 24, 'fields': [
            {'offset': 0, 'bytes': 4, 'meaning': 'command, unchanged in reply'},
            {'offset': 4, 'bytes': 2, 'meaning': 'version=1 in caller, original server copies it'},
            {'offset': 6, 'bytes': 2, 'meaning': 'payload byte count, cmd9=0x70,cmd3=4'},
            {'offset': 8, 'bytes': 4, 'meaning': 'caller reply queue, dynamic'},
            {'offset': 12, 'bytes': 4, 'meaning': 'native status, 0 on successful config/registration'},
            {'offset': 16, 'bytes': 8, 'meaning': 'opaque/reserved, caller zeroes and original server preserves; no stronger semantic name proven'}],
        'wait': 'D+0xf294..0xf2a8: wait on header+8 with timeout=-1 after send succeeds',
        'reply_validation': 'D checks allocation size>23 and returned payload length<=requested; no command/version correlation check here. Provider must still preserve and validate full request.',
        'minimal_provider_commands': 'Only cmd9/config and cmd3/registration are specified for success; remaining13-table commands need separate behavior if observed. Original unknown command returns native0x80000003 with24B reply and payload length0 (K+0x1b60..0x1be0). Never return success for unknown power/PCI/media operations.',
        'no_card': 'Config/registration succeed with status0 even when empty; do not return a no-device error or zero the topology. Detection absence is the separate FRONT port_state bit.'}

    # Explicit synthetic reset epoch. RM1 compatibility state is also modeled, empty;
    # RM2/RM3 are the two actual application slots. 07 is NOT claimed a hardware capture.
    body = bytes.fromhex('02000007000000')
    decoded_ports = [{'rm_port': i+1, 'enable': (body[3] >> i) & 1,
                      'hold': body[4+i] & 1, 'port_state': (body[4+i] >> 1) & 1,
                      'remove_count': body[4+i] >> 4} for i in range(3)]
    proof['front_software_contract'] = {
        'body_bytes': 7, 'body_hex': body.hex(), 'ports': decoded_ports,
        'markers': {'synthetic_empty_slot_provider': 1, 'original_CP': 0},
        'proven_fixed_prefix': '020000 from P+0xab2904..0xab290c',
        'enable_choice': '07: all three native compatibility RM ports enabled and empty; actual slots RM2/RM3 enabled. 06 also yields the same two-slot empty inference but disables compatibility RM1. Neither mask is an observed FX3 CP boot value.',
        'counters': '0 is a new synthetic boot epoch, not an assertion about original hardware history. Keep unchanged for an unchanged empty state; increment only for modeled removal transitions modulo16.',
        'destination': 'Normal original path P ->0x8028017c ->K rm worker ->D registered notify queue. Minimal software provider may own the K cache/replay boundary and send to exact cmd3 payload ID.',
        'source': 'For cached replay set OSAL source to current cmd3 notification destination, exactly K+0x1308..0x1318; original direct CP source unresolved and unnecessary for replay.',
        'timing': ['Register 0x80d9016e before D constructor cmd9.',
                   'Keep a valid snapshot before cmd3; D Init must receive original config masks first.',
                   'On cmd3(nonzero), deliver a fresh allocated7B copy to actual registered ID before cmd3 reply, mirroring K+0x1258..0x1360.',
                   'D callback stores first ObjMsg and sets+0x2a0/signals; constructor starts ThreadInit only after cmd3 returns.',
                   'Require first native Parse/Update to complete and media state2 before StartInOut; do not substitute a delay.',
                   'cmd3(0) unregisters; no delivery to stale destination. Retain snapshot and replay once to each new valid registration.'],
        'ownership': ['Use native OSAL allocation for actual destination and exact payload size.',
                      'Successful osal_snd_msg transfers ownership; sender must not free or reuse that allocation.',
                      'Failure frees once with allocation destination, reports failure, and does not pretend delivery.',
                      'RM original server frees request after bounded copy, allocates separate reply to header+8; caller frees reply.',
                      'Cache bytes, never retain guest request pointer. One owner serializes registration/cache/generation.'],
        'prohibitions': ['No fake capacity, sectors, partition, filesystem, successful mount, or inserted event.',
                         'No direct application parameter write, direct callback invocation, condition flag write, forced dialog close, or GPIO guess.',
                         'If original service exists, do not replace/duplicate its queue. No hardware kernel module initialization is requested.']}
    derivations = []
    for media_id, mask in [(0x1000, 4), (0x1010, 2)]:
        candidate = 3
        any_enabled_empty = False
        for i, p in enumerate(decoded_ports):
            if not mask & (1 << i) or not p['enable']:
                continue
            if p['port_state']:
                candidate = i
                break
            any_enabled_empty = True
        assert candidate == 3 and any_enabled_empty
        # D+0xfbcc..0xfd14: state0 + candidate3 -> state2; Start at state2
        # takes fa04->fa34 with w2=0, skipping fa24 and fa30(status1).
        derivations.append({'media_id': hex(media_id), 'port_mask': mask, 'update_candidate': candidate,
                            'before_state': 0, 'after_state': 2, 'start_notify_statuses': [0],
                            'start_branch': '0xf9fc(w2=0)->0xfa00->0xfa04->0xfa34->0xfa3c',
                            'level': 'B static branch projection, not native runtime execution'})
    proof['empty_slot_branch_projection'] = derivations
    proof['mapping'] = [
        {'slot': 1, 'media_id': '0x1000', 'path': '/nondev/rm3', 'logical_rm': 3, 'physical_rm': 3,
         'mask': 4, 'supported_targets': ['MMC1=0x21', 'PCIe1=0xb1'],
         'evidence': ['L92:18308,18321..18330', 'K+0x10698/0x10b48', 'A event names0x4171670..0x41716a0']},
        {'slot': 2, 'media_id': '0x1010', 'path': '/nondev/rm2', 'logical_rm': 2, 'physical_rm': 2,
         'mask': 2, 'supported_targets': ['MMC0=0x20', 'PCIe0=0xb0'],
         'evidence': ['L92:18817,18831..18840', 'K+0x10698/0x10b48', 'A event names0x4171670..0x41716a0']}]
    proof['limitations'] = [
        'Original live FX3 CP enable mask, reset-epoch removal counters, and publication wall-clock time are not captured; 07/zeros is an explicit software epoch.',
        'CP producer0xab27a6 checks publisher states1/2/3; state2 sends initial notification, state3 compares meaningful bits and sends on change. Exact upstream hardware sampling/init timeline not closed.',
        'Exact original CP OSAL source ID and physical card detect GPIO/polarity remain unresolved; cached AP replay source is closed.',
        'PCI auxiliary field formal names/live values remain unresolved; zero means software has no PCI binding, not real hardware identity.',
        'Correct config plus empty snapshot is required: config alone leaves fallback; first FRONT alone with zero media mask leaves state0 unchanged.',
        'Native config/device queries and reject bookkeeping can still occur in empty state; only the false insertion trigger is removed by this contract.',
        'No-card snapshot does not prevent an unrelated explicit Mount call. M+0x9c98 has no automatic FRONT guard before its query/open path.',
        'No new VM run, original parameter propagation, no-Mount runtime trace, NO CARD pixels, or MENU interaction was performed or accepted.'
    ]
    proof['official_sources'] = [
        {'url': 'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888864.html',
         'checked': '2026-11-02', 'support': 'FX3 Ver2-or-later documents NO CARD=no memory card inserted; illustrations and content can vary with firmware.'},
        {'url': 'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867589.html',
         'checked': '2026-11-02', 'support': 'FX3 documented MENU navigation; not proof of this VM or universal no-card/no-dialog behavior.'}]
    payload = (json.dumps(proof, ensure_ascii=False, indent=2)+'\n').encode()
    path = OUT/'rm-media-proof.json'
    if args.check:
        assert path.read_bytes() == payload, 'proof differs; rebuild and review'
    else:
        path.write_bytes(payload)
    print(json.dumps({'ok': True, 'mode': 'check' if args.check else 'rebuild', 'proof': str(path),
                      'sha256': sha(payload), 'blocks': len(proof['blocks']), 'checks': len(proof['checks']),
                      'no_qemu': True, 'runtime_acceptance': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
