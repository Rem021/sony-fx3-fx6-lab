#!/usr/bin/env python3
"""Read original firmware, kernel references and upstream source; no device backend."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def main():
    inputs = json.loads((HERE / 'inputs-receipt.json').read_text())
    for field in ('selected_kernel_sources', 'original_modules', 'fixed_upstream_sources'):
        for record in inputs[field]:
            p = ROOT / record['path']
            assert p.stat().st_size == record['bytes'] and sha256(p.read_bytes()).hexdigest() == record['sha256']
    prior = BASE / 'stage134-backup-reader-scope-and-service-extension'
    prior_receipt = prior / 'final-receipt.json'
    assert sha256(prior_receipt.read_bytes()).hexdigest() == '5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    pins = json.loads(prior_receipt.read_text())['files']
    references = []
    for path in (prior / 'audit_readers.py', prior / 'upstream/sony.py', prior / 'upstream/usb-commands.py'):
        pin = next(x for x in pins if x['path'] == path.relative_to(ROOT).as_posix())
        assert sha256(path.read_bytes()).hexdigest() == pin['sha256']
        references.append(pin)
    spec = importlib.util.spec_from_file_location('fixed_elf_reader', prior / 'audit_readers.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    common = reader.Image('libInfraUsbCmn.so', '6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396')
    core = reader.Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    common_names = ['_ZN13CUsbGadgetSen9on_createEP7CUsbSvcP19CUSB_GADGET_REGINFOP19CUSB_GADGET_CREINFO',
                    '_ZN13CUsbGadgetSen11proc_keventEmhhPv', '_ZN7CUsbSvc24check_forced_senser_modeEv']
    core_names = ['_ZN3Usb24initialize_usb_interfaceE20usb_port_selection_t',
                  '_ZN3Usb20active_event_handlerE15__SENIF_EVENT_TPhmi',
                  '_ZN3Usb22inactive_event_handlerE15__SENIF_EVENT_TPhmi']
    functions = [{'image': 'libInfraUsbCmn.so', **common.function(n)} for n in common_names]
    functions += [{'image': 'libsencore.so', **core.function(n)} for n in core_names]
    ins = {int(i['pc'], 16): i for f in functions if f['image'] == 'libInfraUsbCmn.so' for i in f['instructions']}
    expected = {0x18d10: 'add x0, x0, #0x460', 0x18d14: 'ldp x2, x3, [x0]',
                0x18d1c: 'stp x2, x3, [x0, #-0x80]!', 0x18d24: 'mov w0, #0x10',
                0x18d6c: 'mov x1, #0xe000', 0x18d70: 'movk x1, #0x4070, lsl #16',
                0x18bf0: 'cmp w1, #1', 0x18bf8: 'cmp w1, #7', 0x18c00: 'cmp w2, #4',
                0x18c08: 'ldr w1, [x3]', 0x18c14: 'mov w5, #2',
                0x18c30: 'cmp w1, #1', 0x18c38: 'mov w5, #3',
                0x18c10: 'ldr x4, [x0, #0xf0]', 0x18c3c: 'ldr x4, [x0, #0xf8]',
                0x18c2c: 'br x4', 0x12108: 'mov w1, #0', 0x1212c: 'mov x2, #3',
                0x12150: 'mov x2, #2', 0x1215c: 'cbz w0, #0x1217c'}
    for pc, text in expected.items():
        assert ins[pc]['asm'] == text, (hex(pc), ins[pc])
    common_calls = [(0x18d74, 'ioctl'), (0x12120, 'open'), (0x12138, 'read'),
                    (0x12158, 'strncmp'), (0x12180, 'close')]
    checked = [common.expect_call(pc, name) for pc, name in common_calls]
    path, marker = common.string(0x1d186), common.string(0x1d199)
    assert (path, marker) == ('/setting/sen/smode', 'UU')

    tree = ast.parse((prior / 'upstream/sony.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SonySenserAuthDevice')
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in cls.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id in ('SONY_VendorRequest_StartSenser', 'SONY_VendorRequest_StopSenser')}
    frames = []
    for label, key in [('start', 'SONY_VendorRequest_StartSenser'), ('stop', 'SONY_VendorRequest_StopSenser')]:
        request, value, index = values[key]
        data = struct.pack('<BBHHH', 0x43, request, value, index, 0)
        frames.append({'purpose': label, 'bmRequestType': '0x43', 'bRequest': request,
                       'wValue': hex(value), 'wIndex': hex(index), 'wLength': 0,
                       'setup_hex': data.hex(), 'inert_data_not_sent': True})
    assert b''.join(bytes.fromhex(x['setup_hex']) for x in frames) == common.read(0x1d460, 16)

    module_path = HERE / 'original-components/kmod/usbg_sen.ko'
    raw = module_path.read_bytes()
    assert sha256(raw).hexdigest() == '1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2'
    elf = ELFFile(io.BytesIO(raw))
    assert elf['e_type'] == 'ET_REL' and elf['e_machine'] == 'EM_AARCH64' and elf.little_endian
    text = elf.get_section_by_name('.text').data()
    symtab = elf.get_section_by_name('.symtab')
    relocations = {r['r_offset']: r for r in elf.get_section_by_name('.rela.text').iter_relocations()}
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    def native(lo, count):
        result = []
        for i in md.disasm(text[lo:lo + count], lo):
            r = relocations.get(i.address)
            target = symtab.get_symbol(r['r_info_sym']) if r is not None else None
            result.append({'section_offset': hex(i.address), 'bytes': i.bytes.hex(),
                           'asm': i.mnemonic + ' ' + i.op_str,
                           'relocation_symbol': target.name if target is not None else None,
                           'relocation_type': r['r_info_type'] if r is not None else None})
        assert sum(len(bytes.fromhex(x['bytes'])) for x in result) == count
        return result
    # Mapping symbols delimit the first code span from its following literal pool.
    mappings = {(s['st_value'], s.name[1]) for s in symtab.iter_symbols()
                if s['st_shndx'] == 2 and s.name.startswith(('$x', '$d'))}
    assert (0, 'x') in mappings and (0xc8, 'd') in mappings and (0xe8, 'x') in mappings
    vendor = native(0, 0xc8)
    ni = {int(i['section_offset'], 16): i for i in vendor}
    for off, sym in [(0x34, 'memcmp'), (0x4c, 'memcmp'),
                     (0x70, 'usb_gadgetcore_stop_other_driver'), (0x98, 'usb_event_add_queue')]:
        assert ni[off]['relocation_symbol'] == sym and ni[off]['relocation_type'] == 283
    for off, assembly in {0x2c: 'mov x2, #8', 0x44: 'add x0, x19, #8',
                          0x48: 'mov x2, #8', 0x68: 'mov w21, #1',
                          0x78: 'cbnz w0, #0xb4', 0x84: 'mov w4, #4',
                          0x88: 'mov w3, #7', 0x90: 'str w21, [x5, #-4]!',
                          0x58: 'mov w0, #2', 0x9c: 'b #0x54'}.items():
        assert ni[off]['asm'] == assembly, ni[off]
    callback_relocation = relocations[0x1a38]
    cb_sym = symtab.get_symbol(callback_relocation['r_info_sym'])
    assert callback_relocation['r_info_type'] == 257 and callback_relocation['r_addend'] == 0
    assert cb_sym['st_info']['type'] == 'STT_SECTION' and cb_sym['st_shndx'] == 2
    registration = native(0x1580, 0x60)
    reg = {int(i['section_offset'], 16): i for i in registration}
    assert reg[0x15c0]['asm'] == 'ldr x2, #0x1a38'
    assert reg[0x15d0]['asm'] == 'str x2, [x24, #0xe0]'
    assert reg[0x158c]['relocation_symbol'] == 'usbg_cmn_copy_probe_info'
    assert reg[0x15d4]['relocation_symbol'] == 'usb_gadgetcore_register_driver'
    stop_symbol = next(s for s in symtab.iter_symbols() if s.name == 'usbg_ldisc_stop')
    native_stop = native(stop_symbol['st_value'], stop_symbol['st_size'])

    kernel_dir = HERE / 'official-kernel-reference/linux-kernel'
    source_path = kernel_dir / 'drivers/usb/gadget/specific_gadget/usbg_sen/usbg_sen_main.c'
    source = source_path.read_text(errors='replace')
    # Preserve raw bytes/hash; replacement decoding is only a display of old comments.
    assert 'sizeof(struct usb_ctrlrequest)' in source and 'USBG_SEN_CMD_NR' in source
    snippets = []
    for first, last in [(437, 502), (1236, 1275)]:
        snippets.append({'path': source_path.relative_to(ROOT).as_posix(),
                         'first_line': first, 'last_line': last,
                         'text': '\n'.join(source.splitlines()[first-1:last])})

    result = {
        'status': 'PASS_STATIC_FX3_VENDOR_HEADERS_KERNEL_DISPATCH_NOT_LIVE_SERVICE_OR_RECOVERY',
        'original_library_functions': functions, 'checked_common_PLT_calls': checked,
        'upstream_reference_pins': references,
        'configured_control_headers': {'VA': '0x1d460', 'bytes': common.read(0x1d460, 16).hex(), 'frames': frames},
        'kernel_vendor_code': {'image_sha256': sha256(raw).hexdigest(), 'code_section': '.text',
            'entry_offset': '0x0', 'span_bytes': 0xc8, 'mapping_delimited_not_STT_FUNC_named': True,
            'native_static_instructions': vendor,
            'registration_prefix': registration,
            'callback_pointer_literal': {'offset': '0x1a38', 'type': 'R_AARCH64_ABS64', 'target_section': '.text', 'addend': 0},
            'behavior': 'Two exact8B setup comparisons; match0/1 -> stop other gadget driver, if success queue4B command id under event7; queue return not checked before constant2 return.',
            'not_proof_host_ACK_waits_for_consumption_or_cancel_join': True},
        'kernel_ldisc_stop': {'section_offset': hex(stop_symbol['st_value']), 'bytes': stop_symbol['st_size'],
                              'instructions': native_stop, 'no_end_to_end_timeout_or_return_proven': True},
        'kernel_reference_snippets': snippets,
        'consumer_boundary': {'function': 'CUsbGadgetSen::proc_kevent', 'VA': '0x18be8',
            'condition': 'common event7 and subtype4, command id from payload',
            'cmd0': 'invoke stored+f0 callback with event2 and zero status',
            'cmd1': 'invoke stored+f8 callback with event3 and zero status',
            'all_registration_dynamic_callbacks_queue_ownership_and_wire_completion_closed': False,
            'distinguish_from_core_SENSER_event1_and2': 'Core active/inactive handlers publish internal4/5; these types cannot be equated solely by matching integers.'},
        'separate_forced_service_file': {'path': path, 'two_byte_marker': marker,
            'reference_open_flags': 0, 'read_max_bytes': 3, 'compare_bytes': 2,
            'different_from_stage136_ramdsk_dev_mode_AA': True,
            'setting_fstab_configured_flash_backed': True,
            'actual_file_exists_or_is_modified_by_this_authentication': False,
            'actual_body_mount_or_coldboot_persistence_verified': False},
        'no_original_Sony_execution_or_device_operations': True,
        'safe_exit_or_independent_recovery_proven': False,
        'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'vendor-dispatch-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'whole_original_library_functions': len(functions),
                      'kernel_vendor_static_code_bytes': len(bytes.fromhex(''.join(x['bytes'] for x in vendor))),
                      'exact_configured_headers': len(frames), 'camera_operations': 0}))


if __name__ == '__main__':
    main()
