#!/usr/bin/env python3
"""Read-only FX3 input audit. Only output: sibling key-input-proof.json.

No emulation, guest commands, original-binary edits, device access or VM startup.
Run with the capstone/pyelftools venv named in COMMON-CONTEXT.md.
"""
import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
VM = ROOT / 'work/fx3-vm-20261101/menu-repair-01'
ORIG = VM / 'original-uipc'
FW = ROOT / 'work/sony-firmware-20261024'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
REMOTE = ('_ZN20infra_wrapper_remote6detail29send_key_event_to_input_infra'
          'ERKNS_34send_key_event_to_input_infra_in_tE'
          'RNS_35send_key_event_to_input_infra_out_tE')
PINS = {
    'app': '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'obj': 'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
    'input': 'd9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057',
    'cp': 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
    'kernel': 'da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c',
    'seed': 'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Elf:
    def __init__(self, path):
        self.path = path
        self.b = path.read_bytes()
        self.e = ELFFile(io.BytesIO(self.b))

    def read(self, va, size):
        s = next(s for s in self.e.iter_segments()
                 if s['p_type'] == 'PT_LOAD' and
                 s['p_vaddr'] <= va and va + size <= s['p_vaddr'] + s['p_filesz'])
        off = va - s['p_vaddr'] + s['p_offset']
        return self.b[off:off + size]

    def plt(self):
        sy = self.e.get_section_by_name('.dynsym')
        pl = self.e.get_section_by_name('.plt')
        re = self.e.get_section_by_name('.rela.plt')
        return {pl['sh_addr'] + 32 + i * 16: sy.get_symbol(z['r_info_sym']).name
                for i, z in enumerate(re.iter_relocations())}


def backup_property(data, base, ident):
    magic, cookie, dirty, rev, ns, np, start, size, checksum = struct.unpack_from('<III4s5I', data, base)
    assert rev == b'BK4\0'
    end = base + start + size
    assert end <= len(data)
    assert sum(data[base:base+32]) + sum(data[base+36:end]) == checksum
    cnt, idx = struct.unpack_from('<HI', data, base+256+(ident >> 16)*6)
    assert (ident & 65535) < cnt and idx + cnt <= np
    prop_at = base + 256 + ns * 6 + (idx + (ident & 65535)) * 6
    attr, ptr = struct.unpack_from('<HI', data, prop_at)
    assert ptr != 0xffffffff
    n, off = ptr >> 24, ptr & 0xffffff
    if n == 255:
        n = struct.unpack_from('<H', data, base+off)[0]
        off += 2
    elif n == 0:
        n, maximum = struct.unpack_from('<HH', data, base+off)
        assert n <= maximum
        off += 4
    assert start <= off and off+n <= start+size
    return data[base+off:base+off+n], {
        'id': hex(ident), 'record_base': hex(base), 'property_table_file_offset': hex(prop_at),
        'file_offset': hex(base+off), 'bytes': n, 'sha256': sha(data[base+off:base+off+n]),
        'record_checksum_matches': True,
    }, (end + 4095) & ~4095


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='compare rebuilt proof without writing')
    args = parser.parse_args()
    vol = subprocess.run(['diskutil', 'info', '-plist', '/Volumes/KAFU2T'],
                         check=True, capture_output=True).stdout
    import plistlib
    assert plistlib.loads(vol)['VolumeUUID'].upper() == UUID
    assert ROOT == Path('/Volumes/KAFU2T/AI/Projects/Mac')
    manifest_path = ORIG / 'ap-projection/full-v5/projection-manifest-full-v5.json'
    manifest = json.loads(manifest_path.read_text())
    ix = manifest['logical_guest_to_payload']
    app = Elf(Path(ix['/usr/lib/appFw.so']['payload_file']))
    obj = Elf(Path(ix['/usr/lib/libObj.so']['payload_file']))
    inp = Elf(Path(ix['/usr/kmod/input.ko']['payload_file']))
    paths = {
        'app': app.path, 'obj': obj.path, 'input': inp.path,
        'cp': FW/'stage2/extraction/files/nflasha8/cpapp-b.bin',
        'kernel': FW/'stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin',
        'seed': ORIG/'original-seeds/FX3-CX95900_ALLLANG-Backup.bin',
        'seed_provenance': ORIG/'original-service-seed-provenance.json',
        'manifest': manifest_path,
        'gpio5': VM/'runtime/qemu-display-build/sources/qemu-11.1.2/hw/misc/fx3_gpio_bank5.c',
        'virt': VM/'runtime/qemu-display-build/sources/qemu-11.1.2/hw/arm/virt.c',
        'config': FW/'stage133-FX5-source-availability-and-portability/fx3-gpl-reference/linux-kernel/arch/arm64/configs/cxd90057_set_defconfig',
        'serial': VM/'runtime/runs/ap66lut-ed5764ad/serial.log',
        'init': FW/'stage129-AP-DMM-config-and-device-trial-plan/inputs/insmod_drv2',
    }
    blobs = {k: p.read_bytes() for k, p in paths.items()}
    for k, pin in PINS.items():
        assert sha(blobs[k]) == pin, (k, 'original changed')
    proof = {
        'schema': 'fx3-key-input-static-audit-v1',
        'scope': 'Static original instructions/tables and existing AP66 log only; no QEMU/guest execution or injection.',
        'sources': {k: {'path': str(p), 'bytes': len(blobs[k]), 'sha256': sha(blobs[k])}
                    for k, p in paths.items()},
        'blocks': {}, 'checks': [],
    }
    cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    thumb = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

    def block(key, source, start, size, section=None):
        elf = {'app': app, 'obj': obj, 'input': inp}.get(source)
        if section:
            raw = elf.e.get_section_by_name(section).data()[start:start+size]
        elif source == 'cp':
            raw = blobs['cp'][start-0x108000:start-0x108000+size]
        else:
            raw = elf.read(start, size)
        md = thumb if source == 'cp' else cs
        ins = [{'va': hex(i.address), 'bytes': bytes(i.bytes).hex(),
                'instruction': (i.mnemonic+' '+i.op_str).strip()}
               for i in md.disasm(raw, start)]
        proof['blocks'][key] = {'source': source, 'section': section,
            'start': hex(start), 'bytes': len(raw), 'sha256': sha(raw), 'instructions': ins}
        return {int(i['va'], 16): i['instruction'] for i in ins}

    blocks = [
        ('cp_native_sender', 'cp', 0x49b8c8, 0x128, None),
        ('cp_front_and_gpio_names', 'cp', 0x49bd68, 0x70, None),
        ('driver_native_sender', 'input', 0x12f0, 0x154, '.text'),
        ('driver_gpio_poll', 'input', 0x1f48, 0x68, '.text'),
        ('driver_front_query', 'input', 0xc0, 0xa8, '.text'),
        ('driver_adc_query', 'input', 0x0, 0xc0, '.text'),
        ('driver_config_load', 'input', 0x0, 0x1e0, '.init.text'),
        ('driver_config_categories', 'input', 0x1fc, 0xa0, '.init.text'),
        ('driver_timer_poll', 'input', 0x4520, 0x15c, '.text'),
        ('obj_receiver', 'obj', 0xcb5e0, 0x590, None),
        ('obj_cache', 'obj', 0xc9c08, 0x54, None),
        ('obj_key_search', 'obj', 0xc9bb4, 0x54, None),
        ('obj_instance', 'obj', 0xc8bb4, 0xe0, None),
        ('obj_send', 'obj', 0xcd79c, 0x168, None),
        ('obj_test_send_event', 'obj', 0xd05d8, 0xbc, None),
        ('obj_test_command_dispatch', 'obj', 0xd01e4, 0x9c, None),
        ('obj_key_config_read', 'obj', 0xcd904, 0x218, None),
        ('obj_config_select', 'obj', 0xcd4bc, 0x5c, None),
        ('obj_event_thread', 'obj', 0xc90b8, 0x90, None),
        ('obj_callback_dispatch', 'obj', 0xc8dec, 0x164, None),
        ('app_remote', 'app', 0x2ddf474, 0x40, None),
        ('app_map_init', 'app', 0x15948e4, 0x50, None),
        ('app_map_lookup', 'app', 0x16ee3b8, 0x48, None),
        ('app_register', 'app', 0x16ef2a0, 0xa4, None),
        ('app_cache_read', 'app', 0x16ef140, 0x60, None),
    ]
    decoded = {key: block(key, src, a, n, sec) for key, src, a, n, sec in blocks}

    def expect(key, va, instruction):
        actual = decoded[key][va]
        assert actual == instruction, (key, hex(va), actual, instruction)
        proof['checks'].append({'block': key, 'va': hex(va), 'instruction': actual, 'pass': True})

    for x in [
        ('driver_native_sender', 0x1318, 'mov w2, #0x14'),
        ('driver_native_sender', 0x1320, 'movk w0, #0x807a, lsl #16'),
        ('driver_native_sender', 0x13b0, 'movk w1, #0x41, lsl #16'),
        ('driver_native_sender', 0x13d0, 'stp w21, wzr, [x2]'),
        ('driver_native_sender', 0x13d4, 'stp w22, w23, [x2, #8]'),
        ('driver_native_sender', 0x13dc, 'str w20, [x2, #0x10]'),
        ('cp_native_sender', 0x49b8de, 'movs r2, #0x14'),
        ('cp_native_sender', 0x49b8e4, 'movt r4, #0x807a'),
        ('cp_native_sender', 0x49b924, 'movt r1, #0x41'),
        ('cp_native_sender', 0x49b940, 'strd sl, fp, [r1]'),
        ('cp_native_sender', 0x49b944, 'strd sb, r6, [r1, #8]'),
        ('cp_native_sender', 0x49b948, 'str r5, [r1, #0x10]'),
        ('obj_receiver', 0xcb650, 'bl #0x56190'),
        ('obj_receiver', 0xcb754, 'ldp x0, x1, [x25]'),
        ('obj_receiver', 0xcb768, 'mov w25, #1'),
        ('obj_receiver', 0xcb78c, 'str w25, [x29, #0x98]'),
        ('obj_receiver', 0xcbb48, 'mov w1, #0x804c'),
        ('obj_receiver', 0xcbb54, 'mov w3, #0x1c'),
        ('obj_key_search', 0xc9bdc, 'ldr w7, [x7, #8]'),
        ('obj_cache', 0xc9c28, 'ldr x1, [x20, #0x38]'),
        ('obj_cache', 0xc9c30, 'ldr w0, [x1, #8]'),
        ('obj_instance', 0xc8bcc, 'ldr x0, [x19, #0xe48]'),
        ('obj_test_send_event', 0xd05e4, 'mov w1, #0x20'),
        ('obj_test_send_event', 0xd05f8, 'mov w3, #0x14'),
        ('obj_test_send_event', 0xd0620, 'bl #0xcd79c'),
        ('obj_test_command_dispatch', 0xd0270, 'b.eq #0xd05d8'),
        ('app_remote', 0x2ddf49c, 'bl #0x15933e0'),
        ('app_register', 0x16ef2f8, 'mov w3, #0x43e'),
        ('driver_config_load', 0x38, 'mov w0, #0x1120000'),
        ('driver_config_load', 0x1dc, 'lsr w26, w26, #6'),
        ('obj_callback_dispatch', 0xc8e2c, 'blr x2'),
    ]:
        expect(*x)

    # Resolve module relocations, including section-relative addresses.
    sy = inp.e.get_section_by_name('.symtab')
    relocs = {}
    for sn in ['.rela.text', '.rela.init.text', '.rela.rodata']:
        rows = []
        for r in inp.e.get_section_by_name(sn).iter_relocations():
            sym = sy.get_symbol(r['r_info_sym'])
            rows.append({'offset': hex(r['r_offset']), 'symbol': sym.name,
                         'symbol_section': sym['st_shndx'], 'addend': hex(r['r_addend']),
                         'type': r['r_info_type']})
        relocs[sn] = rows
    proof['input_relocations'] = relocs
    funcs = {int(r['offset'], 16): r['symbol'] for r in relocs['.rela.text']}
    assert funcs[0x132c] == 'osal_valloc_msg_wait'
    assert funcs[0x13b8] == 'osal_set_msg_src' and funcs[0x13e0] == 'osal_snd_msg'
    assert funcs[0x1f80] == 'gpio_get_data_bit'
    undef = sorted(z.name for z in sy.iter_symbols() if z['st_shndx'] == 'SHN_UNDEF' and z.name)
    assert 'input_register_device' not in undef and 'input_event' not in undef
    proof['input_kernel_undefined_symbols'] = undef
    cat = {}
    for r in inp.e.get_section_by_name('.rela.rodata').iter_relocations():
        if 0x48 <= r['r_offset'] <= 0x80:
            sym = sy.get_symbol(r['r_info_sym'])
            s = inp.e.get_section(sym['st_shndx'])
            n = s.data()[r['r_addend']:].split(b'\0')[0].decode()
            cat[(r['r_offset']-0x48)//8] = n
    assert cat == {0: '[end]', 1: 'ADC', 2: 'GPIO', 3: 'GPINT', 4: 'FRONT', 5: 'GPIRQ', 6: 'SIRCS', 7: 'VGRIP'}
    proof['hardware_categories'] = cat

    # UI enum names are linked to string pointers in a {u32 value,u32 length,u64 ptr} table.
    wanted = ['TACT_MENU', 'TACT_UP', 'TACT_DOWN', 'TACT_LEFT', 'TACT_RIGHT', 'TACT_ENTER',
              'DIAL_ASSIGN_REAR_DIAL', 'DIAL_ASSIGN_REAR_DIAL2', 'DIAL_ASSIGN_FRONT_DIAL',
              'DIAL_ASSIGN_CONTROL_WHEEL', 'OTHER_WHEEL', 'OTHER_WHEEL2', 'OTHER_WHEEL3',
              'OTHER_KURU_LEFT', 'OTHER_KURU_RIGHT', 'OTHER_WHEEL_LEFT', 'OTHER_WHEEL_RIGHT']
    names = {}
    for suffix in wanted:
        name = 'UIBIZ_KEY_'+suffix
        off = app.b.find(name.encode()+b'\0')
        assert off >= 0, name
        seg = next(s for s in app.e.iter_segments() if s['p_type']=='PT_LOAD' and
                   s['p_offset']<=off<s['p_offset']+s['p_filesz'])
        names[off-seg['p_offset']+seg['p_vaddr']] = name
    enums = {}
    for sec in app.e.iter_sections():
        if sec['sh_type'] != 'SHT_RELA':
            continue
        for r in sec.iter_relocations():
            if r['r_addend'] in names:
                va = r['r_offset']
                value, length = struct.unpack('<II', app.read(va-8, 8))
                name = names[r['r_addend']]
                assert length == len(name)+1
                enums[name] = {'ui_code': hex(value), 'name_va': hex(r['r_addend']),
                               'enum_record_va': hex(va-8)}
    assert len(enums) == len(wanted)
    pairs = list(struct.iter_unpack('<II', app.read(0x2f8f8d8, 0x22d0)))
    for name, row in enums.items():
        matches = [(i, y) for i, (x,y) in enumerate(pairs) if x == int(row['ui_code'],16)]
        row['infra_bindings'] = [{'map_va': hex(0x2f8f8d8+i*8), 'infra_code': hex(y)} for i,y in matches]
        row['mapping_proven'] = bool(matches)
    expected = {'TACT_MENU': 0x1ab, 'TACT_UP': 3, 'TACT_LEFT': 0x15,
                'TACT_DOWN': 0x30, 'TACT_RIGHT': 0x1af, 'TACT_ENTER': 0x1ac}
    for suffix, value in expected.items():
        assert enums['UIBIZ_KEY_'+suffix]['infra_bindings'][0]['infra_code'] == hex(value)
    proof['keys'] = enums

    seed = blobs['seed']
    logical, meta, nextrec = backup_property(seed, 0, 0x7a0001)
    assert struct.unpack_from('<4I', logical) == (0x214e4942,0xd080,2,0xd080)
    fields = ['keyName', 'infraName', 'keyCode', 'localCode', 'priority', 'repeat_time0_ms',
              'repeat_time_ms', 'group', 'flag', 'osalId', 'dummy1', 'dummy2']
    logical_rows = []
    for at in range(16,16+0xd080,48):
        vals = struct.unpack_from('<12I', logical, at)
        logical_rows.append({'file_offset': hex(int(meta['file_offset'],16)+at),
                             **dict(zip(fields, vals))})
    assert len(logical_rows) == 1112
    selected_codes = {int(v['infra_code'],16) for z in enums.values() for v in z['infra_bindings']}
    proof['logical_config'] = {'property': meta, 'row_bytes': 48, 'rows': len(logical_rows),
        'selected': [r for r in logical_rows if r['keyCode'] in selected_codes]}
    hardware = []
    for seq, base in enumerate([0, nextrec]):
        raw, metadata, _ = backup_property(seed, base, 0x1120000)
        count = struct.unpack_from('<I', raw, 16)[0]
        assert count == 1
        lengths = struct.unpack_from('<I', raw, 20)
        start = 24
        rows = []
        assert lengths[0] % 64 == 0
        for at in range(start,start+lengths[0],64):
            vals = struct.unpack_from('<16I', raw, at)
            rows.append({'file_offset': hex(int(metadata['file_offset'],16)+at),
                         'raw64': raw[at:at+64].hex(), 'u32': list(vals),
                         'category': cat[vals[1]], 'category_id': vals[1],
                         'unit_or_gpio_bank': vals[2], 'channel_or_bit': vals[3],
                         'active_level': vals[4], 'key_code': hex(vals[9]),
                         'on_value': hex(vals[10]), 'ex_info': hex(vals[11])})
        hardware.append({'template_record': seq, 'property': metadata, 'tables': count,
                         'selected_table': 0, 'table_bytes': lengths[0], 'rows': rows})
    menu_hw = [r for r in hardware[1]['rows'] if r['key_code']=='0x1ab']
    assert len(menu_hw)==1 and (menu_hw[0]['category_id'],menu_hw[0]['unit_or_gpio_bank'],
           menu_hw[0]['channel_or_bit'],menu_hw[0]['active_level']) == (4,0x6000,2,0)
    proof['hardware_config'] = hardware
    provenance = json.loads(blobs['seed_provenance'])['records'][0]
    assert provenance['sha256'] == sha(seed)
    proof['template_provenance'] = {k: provenance[k] for k in
        ['source_fdat','source_fdat_sha256','tar_member','absolute_data_offset','sha256','bytes']}

    # Complete original projection, not only the smaller regular-files directory.
    defs, imports, elf_rows, module_rows = [], [], [], []
    for gp,row in sorted(ix.items()):
        if row.get('type')!='regular':
            continue
        p = Path(row['payload_file'])
        with p.open('rb') as f:
            if f.read(4)!=b'\x7fELF':
                continue
            f.seek(0)
            e = ELFFile(f)
            assert sha(p.read_bytes()) == row['sha256']
            elf_rows.append({'guest_path': gp, 'sha256': row['sha256']})
            if gp.endswith('.ko'):
                module_rows.append({'guest_path': gp, 'sha256': row['sha256'], 'payload': str(p)})
            sy = e.get_section_by_name('.dynsym')
            if sy:
                for sym in sy.iter_symbols():
                    if sym.name == REMOTE:
                        target = imports if sym['st_shndx']=='SHN_UNDEF' else defs
                        target.append({'guest_path': gp,'value':hex(sym['st_value']),
                                       'bind': sym['st_info']['bind'],'visibility':sym['st_other']['visibility']})
    assert app.plt()[0x15933e0] == REMOTE
    assert obj.plt()[0x56190] == 'osal_rcv_msg_tmo'
    proof['remote_import'] = {'symbol': REMOTE, 'call_va':'0x2ddf49c', 'plt_va':'0x15933e0',
        'imports':imports,'defined_providers':defs,'scanned_elfs':elf_rows,
        'scope':'Dynamic exported providers in complete full-v5 projection; no claim about unavailable partitions or future dlopen providers.'}
    proof['modules'] = module_rows
    proof['linux_input_path'] = {
        'config_lines':[l for l in blobs['config'].decode().splitlines()
                        if re.search(r'CONFIG_(INPUT(?:=|_)|GPIOLIB|KEYBOARD)',l)],
        'kernel_ikconfig_magic_present':b'IKCFG_ST' in blobs['kernel'],
        'projection_dev_input_members':[p for p in ix if p.startswith('/dev/input') or p=='/dev/uinput'],
        'uinput_module_present':any(p.endswith('/uinput.ko') for p in ix),
        'input_ko_is_vendor_osal_driver':True,
        'actual_guest_dev_input_inventory':'Not observed live in this read-only audit; empty archive entries are not devtmpfs absence proof.',
        'official_reference':'https://docs.kernel.org/input/uinput.html',
    }
    assert '# CONFIG_INPUT_KEYBOARD is not set' in blobs['config'].decode()
    assert '# CONFIG_INPUT_MISC is not set' in blobs['config'].decode()
    assert '# CONFIG_GPIOLIB is not set' in blobs['config'].decode()
    proof['existing_runtime_evidence'] = [
        {'line':i+1,'text':l} for i,l in enumerate(blobs['serial'].decode(errors='replace').splitlines())
        if 'FX3_UIPC_RECV_BEGIN' in l and 'I-InputRecv' in l or '__boottime_evdev_init' in l
    ]
    assert any('queue=0x807a0020' in r['text'] for r in proof['existing_runtime_evidence'])
    proof['gpio5_limits'] = {'source_lines':[
        {'line':i+1,'text':l} for i,l in enumerate(blobs['gpio5'].decode().splitlines())
        if any(k in l for k in ['No input signal','off==0x10','group==1','sysbus_init_mmio'])],
        'virt_mapping_lines':[
            {'line':i+1,'text':l} for i,l in enumerate(blobs['virt'].decode().splitlines())
            if 3175 <= i+1 <= 3182],
        'input_irq_exists':False,
    }
    assert 'sysbus_init_irq' not in blobs['gpio5'].decode()
    assert 'insmod /usr/kmod/input.ko' in blobs['init'].decode()
    menu = next(r for r in logical_rows if r['keyCode']==0x1ab)
    assert menu['osalId']==0x00410025 and menu['repeat_time0_ms']==menu['repeat_time_ms']==0
    proof['recommended_contract'] = {
        'stage':'Implementation-ready static candidate; not injected or runtime accepted.',
        'transport':'Original in-process libosal allocator + source setter + sender, as capid helper already uses.',
        'target_queue':'0x807a0020', 'source_id':'0x00410025', 'payload_bytes':20,
        'fields_u32_le':['key_code','sub_key_code','status','ex_info','from_type'],
        'menu_down':struct.pack('<5I',0x1ab,0,1,0,1).hex(),
        'menu_up':struct.pack('<5I',0x1ab,0,0,0,1).hex(),
        'ownership':'Successful osal_snd_msg transfers buffer; free an allocated buffer only if send fails. Allocation failure creates no buffer to free.',
        'gates':['same im process; original InfraInput exists and I-InputRecv is waiting',
                 'boot barrier cleared; do not inject during failed AP74/75 startup',
                 'observe down consumed/cache update before up; no invented fixed sleep',
                 'verify original callbacks/UI separately from transport'],
        'cache':{'instance_global':'libObj+0x2cde48','config_ptr_offset':'0x20','row_count_offset':'0x2c',
                 'config_row_bytes':48,'key_code_in_config':'0x8','status_ptr_offset':'0x38',
                 'status_row_bytes':44,'status_in_row':'0x8'},
    }
    proof['unproven'] = [
        'Physical PCB wiring and current camera calibration/settings; templates are public same-model defaults.',
        'Exact SysCon-to-CP FRONT packet/register/interrupt producer, and full original CP startup.',
        'Actual loaded input.ko and live /dev/input inventory in current VM.',
        'Input callback -> visible menu and menu display/barrier readiness.',
        'Dial direction, wrap, delta semantics and physical front/rear/control-wheel assignment beyond named enum mapping.',
        'No infra mapping for a UI name is reported as unproven rather than guessed.',
        'Missing remote symbol ABI/implementation and lazy-binding failure if that wrapper is invoked.',
    ]
    output = (json.dumps(proof, ensure_ascii=False, indent=2)+'\n').encode()
    path = OUT/'key-input-proof.json'
    if args.check:
        assert path.read_bytes()==output, 'proof differs from reconstruction'
    else:
        path.write_bytes(output)
    print(json.dumps({'result':'PASS','checks':len(proof['checks']),
        'key_names':len(enums),'original_elfs_scanned':len(elf_rows),'modules':len(module_rows),
        'remote_providers':len(defs),'proof_sha256':sha(output),'proof':str(path)},ensure_ascii=False))


if __name__ == '__main__':
    main()
