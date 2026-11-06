#!/usr/bin/env python3
"""Trace original callback/table copies statically; never access a device."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def load_reader():
    directory = BASE / 'stage134-backup-reader-scope-and-service-extension'
    receipt = directory / 'final-receipt.json'
    assert sha256(receipt.read_bytes()).hexdigest() == '5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
    source = directory / 'audit_readers.py'
    pin = next(x for x in json.loads(receipt.read_text())['files'] if x['path'] == source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('fixed_reader', source)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader


def main():
    reader = load_reader()
    common = reader.Image('libInfraUsbCmn.so', '6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396')
    core = reader.Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    common_names = ['usbif_initialize', 'usb_senif_init',
        '_ZN7CUsbSvc14registerGadgetE8CUSB_FIDP19CUSB_GADGET_REGINFO',
        '_ZN10CUsbGadget12createGadgetEP7CUsbSvcP19CUSB_GADGET_REGINFOP19CUSB_GADGET_CREINFO',
        '_ZN13CUsbGadgetSen11proc_keventEmhhPv', '_ZN7CUsbSvc4stopE11__USBIF_DIDPvhPFS1_S1_S1_hiE',
        '_ZN7CUsbSvc11stop_gadgetEPvhPFS0_S0_S0_hiE',
        '_ZN4CUsb7requestEP8CUSB_MES', '_ZN4CUsb8que_pushEPS_P8CUSB_MES', '_ZN4CUsb12proc_serviceEPv']
    core_names = ['senif_init', '_ZN3Usb24initialize_usb_interfaceE20usb_port_selection_t',
        '_ZN3Usb20active_event_handlerE15__SENIF_EVENT_TPhmi',
        '_ZN3Usb22inactive_event_handlerE15__SENIF_EVENT_TPhmi',
        '_ZN3Usb12handle_inputER20InitiationDispatcher',
        '_ZN3Usb4stopEPFv13__USBIF_EVENTP17usbif_event_paramiE',
        '_ZN3Usb13stop_callbackE13__USBIF_EVENTP17usbif_event_parami',
        '_ZN19WorkerThreadManager4joinEv']
    functions = [{'image': 'libInfraUsbCmn.so', **common.function(n)} for n in common_names]
    functions += [{'image': 'libsencore.so', **core.function(n)} for n in core_names]
    local_spans = [
        {'name': 'Sen gadget registration helper', 'VA': '0x19364', 'bytes': 208},
        {'name': 'common gadget event to SENSER callback', 'VA': '0x18fe4', 'bytes': 280},
        {'name': 'USB interface stop request wrapper', 'VA': '0x17c4c', 'bytes': 344}]
    for f in local_spans:
        address = int(f['VA'], 16)
        f['sha256'] = sha256(common.read(address, f['bytes'])).hexdigest()
        f['instructions'] = common.instructions(address, f['bytes'])
        f['not_exported_STT_FUNC_name'] = True
    ci = {int(i['pc'], 16): i for f in functions if f['image'] == 'libInfraUsbCmn.so' for i in f['instructions']}
    ci.update({int(i['pc'], 16): i for f in local_spans for i in f['instructions']})
    si = {int(i['pc'], 16): i for f in functions if f['image'] == 'libsencore.so' for i in f['instructions']}
    common_expected = {0x193bc: 'adrp x2, #0x33000', 0x193c0: 'add x2, x2, #0x268',
        0x193e4: 'str x1, [x0, #0x158]',
        0x11568: 'mov x2, #0x50', 0x1156c: 'add x0, x0, #0x18',
        0x10438: 'add x4, x19, #0xe0', 0x10444: 'mov x2, #0x50',
        0x18ff4: 'ldr x1, [x3, #0x158]', 0x18ffc: 'ldr x1, [x1]',
        0x19004: 'ldr x2, [x1, #0x18]', 0x19020: 'cmp w0, #3',
        0x190bc: 'ldr x20, [x2, #8]', 0x190e4: 'mov w0, #2',
        0x190a4: 'mov w3, #0', 0x190ac: 'mov x2, #0x20', 0x190b0: 'br x4',
        0x17e1c: 'add x0, x0, #0xc4c', 0x17e20: 'str x0, [x19, #0x18]',
        0x17d3c: 'stp x21, x22, [x20]', 0x17d40: 'str w19, [x20, #0x10]',
        0xf378: 'str x1, [x1, #8]', 0xf3b8: 'cbnz w0, #0xf3dc',
        0xf3e4: 'mov w20, w0', 0xf400: 'cbnz w20, #0xf398',
        0xf404: 'mov w0, #0', 0xf310: 'mov w0, #0xc',
        0xf31c: 'ubfiz x4, x3, #6, #8', 0xf348: 'strb w2, [x0, #0x29]',
        0xf554: 'ldr x1, [x20, #0x10]', 0xf55c: 'blr x1'}
    for pc, asm in common_expected.items():
        assert ci[pc]['asm'] == asm, (hex(pc), ci[pc])
    for pc, asm in {0xca10: 'mov w1, #5', 0xc668: 'mov w0, #-0x7c',
                    0xc67c: 'mov w1, #0xd', 0xc688: 'blr x3',
                    0xcd18: 'cmp w0, #2', 0xc904: 'mov w1, #3'}.items():
        assert si[pc]['asm'] == asm, (hex(pc), si[pc])
    checked = []
    for pc, symbol in [(0x193d0, 'usbif_register_gadget'), (0x11570, 'memcpy'), (0x10448, 'memcpy'),
                       (0x17d44, '_ZN7CUsbSvc4stopE11__USBIF_DIDPvhPFS1_S1_S1_hiE'),
                       (0xf3b4, '_ZN4CUsb8que_pushEPS_P8CUSB_MES'),
                       (0xf3d8, 'pthread_cond_signal'), (0xf3e0, 'pthread_mutex_unlock')]:
        checked.append(common.expect_call(pc, symbol))
    for pc, symbol in [(0xcb1c, 'senif_init'), (0xca18, '_ZNK3Usb4pushENS_10event_typeE'),
                       (0xcd50, '_ZN3Usb4stopEPFv13__USBIF_EVENTP17usbif_event_paramiE'),
                       (0xc660, '_ZN19WorkerThreadManager6cancelEv'),
                       (0xc908, '_ZNK3Usb4pushENS_10event_typeE'),
                       (0xcd78, '_ZN19WorkerThreadManager4joinEv')]:
        checked.append(core.expect_call(pc, symbol))
    bindings = []
    for label, image, addresses in [
        ('common', common, list(range(0x33268, 0x332a8, 8)) + [0x33570]),
        ('core', core, [0x6af98, 0x6b918, 0x6b920, 0x6b9f8])]:
        for r in image.elf.get_section_by_name('.rela.dyn').iter_relocations():
            if r['r_offset'] in addresses:
                s = image.dynsym.get_symbol(r['r_info_sym'])
                bindings.append({'image': label, 'relocation': hex(r['r_offset']), 'type': r['r_info_type'],
                                 'symbol': s.name, 'defined_here': s['st_shndx'] != 'SHN_UNDEF',
                                 'target_or_addend': hex(s['st_value'] + r['r_addend'])})
    callback_table = [x for x in bindings if x['image'] == 'common' and 0x33268 <= int(x['relocation'], 16) < 0x332a8]
    assert len(callback_table) == 8 and all(x['target_or_addend'] == '0x18fe4' for x in callback_table)
    assert next(x for x in bindings if x['relocation'] == '0x6b9f8')['symbol'] == 'usb_senif_pub'
    assert next(x for x in bindings if x['relocation'] == '0x33570')['symbol'] == 'usb_senif_init'
    assert next(x for x in bindings if x['relocation'] == '0x6b920')['target_or_addend'] == '0xc9c0'
    assert core.read(0x16ae0, 7).hex() == '001eee35051e0e'
    # Core init passes these two callbacks into the common context at +18.
    assert ci[0x19448]['asm'] == 'str x2, [x1, #0x18]'
    result = {
        'status': 'PASS_STATIC_FX3_STOP_CALLBACK_BRIDGE_WITH_QUEUE_STATUS_GAP_NOT_LIVE_EXIT',
        'original_functions': functions, 'local_original_spans': local_spans,
        'checked_PLT_calls': checked, 'relocation_bindings': bindings,
        'normal_provider_binding_assumption_not_measured_on_body': True,
        'conditional_stop_chain': [
            'stage138 exact vendor setup -> kernel queues command1; original gadget proc invokes object+f8 with common event3',
            'two80B copies preserve registration+18 callback into gadget+f8; all eight original callbacks target common0x18fe4',
            'common callback resolves context+18 callback table, invokes second entry with SENSER event2, payload pointer and length32, status0',
            'core callback table second entry is Usb::inactive_event_handler; clear channel and push internal event5',
            'internal5 -> core handle_input0xcd14; when USB state2, request USB stop with DID13 and stop_callback',
            'USB API slot18 installed as common0x17c4c; builds24B callback record and calls CUsbSvc.stop',
            'later original stop_callback clears state and posts internal3; handler joins workers before end callbacks'],
        'not_all_live_queue_callbacks_and_worker_cleanup_completed': True,
        'queue_return_gap': {
            'enqueue_function': 'CUsb::que_push', 'full_return': 12, 'message_copy_bytes': 64,
            'request_overwrites_enqueue_status_with_mutex_unlock_status': True,
            'request_zero_is_not_enqueue_or_completion_proof': True,
            'request_error_can_follow_already_queued_message': True,
            'raw_pointer_fields_are_not_deep_copied': True,
            'real_queue_capacity_thread_ownership_concurrency_and_delivery_not_measured': True},
        'original_execution_this_script': False, 'new_device_or_driver_operations': 0,
        'live_service_trial_or_persistent_flash_released': False, 'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'callback-bridge-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'whole_original_functions': len(functions),
                      'local_original_spans': len(local_spans), 'checked_calls': len(checked)}))


if __name__ == '__main__':
    main()
