#!/usr/bin/env python3
"""Bounded original AArch64 request/queue emulation with declared mutex fixtures."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_INTR
from unicorn import arm64_const as reg

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
LOAD = 0x10000000
DATA = 0x40000000
STACK = 0x50000000
RETURN = 0x60000000
CONTEXT, MESSAGE, RING = DATA + 0x1000, DATA + 0x2000, DATA + 0x3000
SAVED_SP = STACK + 0xf000


def main():
    spec = importlib.util.spec_from_file_location('local_bridge_audit', HERE / 'audit_callback_bridge.py')
    local = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(local)
    reader = local.load_reader()
    image = reader.Image('libInfraUsbCmn.so', '6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396')
    request = image.function('_ZN4CUsb7requestEP8CUSB_MES')
    queue = image.function('_ZN4CUsb8que_pushEPS_P8CUSB_MES')
    assert request['VA'] == '0xf354' and request['bytes'] == 184
    assert queue['VA'] == '0xf2cc' and queue['bytes'] == 136
    cases = [
        {'id': 'empty_enqueue', 'head': 0, 'tail': 0, 'expected_return': 0, 'accepted': True, 'new_tail': 1},
        {'id': 'full_but_request_returns0', 'head': 1, 'tail': 0, 'expected_return': 0, 'accepted': False, 'new_tail': 0},
        {'id': 'wrap_enqueue', 'head': 2, 'tail': 3, 'expected_return': 0, 'accepted': True, 'new_tail': 0},
        {'id': 'wrap_full_but_request_returns0', 'head': 0, 'tail': 3, 'expected_return': 0, 'accepted': False, 'new_tail': 3},
        {'id': 'mutex_lock_failure', 'head': 0, 'tail': 0, 'lock': 13, 'expected_return': 5, 'accepted': False, 'new_tail': 0},
        {'id': 'unlock_failure_after_enqueue', 'head': 0, 'tail': 0, 'unlock': 1, 'expected_return': 5, 'accepted': True, 'new_tail': 1},
        {'id': 'signal_failure_after_enqueue', 'head': 0, 'tail': 0, 'signal': 22, 'expected_return': 0, 'accepted': True, 'new_tail': 1},
        {'id': 'full_and_unlock_failure', 'head': 1, 'tail': 0, 'unlock': 1, 'expected_return': 5, 'accepted': False, 'new_tail': 0}]
    output = HERE / 'run-queue-return'
    output.mkdir(exist_ok=False)
    source = Path(__file__).read_bytes()
    (output / 'executed-source.py').write_bytes(source)
    results = []
    code_intervals = [(LOAD + int(f['VA'], 16), LOAD + int(f['VA'], 16) + f['bytes']) for f in (request, queue)]
    plt = {LOAD + addr: name for addr, name in image.plt.items()}
    permitted_calls = {'usb_trace_out', 'pthread_mutex_lock', 'pthread_mutex_unlock', 'pthread_cond_signal', '_ZN4CUsb8que_pushEPS_P8CUSB_MES'}
    for case in cases:
        uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        pages = sorted({address for s in image.loads
                        for address in range((LOAD + s['p_vaddr']) & ~0xfff,
                                             (LOAD + s['p_vaddr'] + s['p_memsz'] + 0xfff) & ~0xfff, 0x1000)})
        for address in pages:
            uc.mem_map(address, 0x1000)
        for s in image.loads:
            uc.mem_write(LOAD + s['p_vaddr'], s.data())
        uc.mem_map(DATA, 0x10000)
        uc.mem_map(STACK, 0x10000)
        uc.mem_map(RETURN, 0x1000)
        uc.mem_write(STACK, bytes([0xa7]) * 0x10000)
        uc.mem_write(CONTEXT, bytes([0x35]) * 0x200)
        uc.mem_write(CONTEXT + 0x20, struct.pack('<Q', RING))
        uc.mem_write(CONTEXT + 0x28, bytes([case['head'], case['tail'], 4]))
        original_ring = bytes([0xc5]) * 256
        guard = bytes([0xda]) * 32
        uc.mem_write(RING - 32, guard + original_ring + guard)
        original_message = bytes((0x40 + n) & 0xff for n in range(64))
        uc.mem_write(MESSAGE - 32, guard + original_message + guard)
        context_before = bytes(uc.mem_read(CONTEXT, 0x200))
        uc.reg_write(reg.UC_ARM64_REG_SP, SAVED_SP)
        uc.reg_write(reg.UC_ARM64_REG_X0, CONTEXT)
        uc.reg_write(reg.UC_ARM64_REG_X1, MESSAGE)
        uc.reg_write(reg.UC_ARM64_REG_X30, RETURN)
        saved = {}
        for n in range(19, 30):
            value = 0xabc00000 + n
            saved[n] = value
            uc.reg_write(getattr(reg, 'UC_ARM64_REG_X' + str(n)), value)
        calls, writes, executed = [], [], []
        def code(machine, pc, size, unused):
            executed.append(pc)
            if pc in plt:
                name = plt[pc]
                assert name in permitted_calls, (case['id'], 'unapproved external target', name)
                x0 = machine.reg_read(reg.UC_ARM64_REG_X0)
                calls.append({'name': name, 'x0': hex(x0)})
                if name == '_ZN4CUsb8que_pushEPS_P8CUSB_MES':
                    assert x0 == CONTEXT and machine.reg_read(reg.UC_ARM64_REG_X1) == MESSAGE
                    machine.reg_write(reg.UC_ARM64_REG_PC, LOAD + int(queue['VA'], 16))
                    return
                if name.startswith('pthread_mutex_'):
                    assert x0 == CONTEXT + 0x70
                if name == 'pthread_cond_signal':
                    assert x0 == CONTEXT + 0xa0
                value = {'pthread_mutex_lock': case.get('lock', 0),
                         'pthread_mutex_unlock': case.get('unlock', 0),
                         'pthread_cond_signal': case.get('signal', 0), 'usb_trace_out': 0}[name]
                machine.reg_write(reg.UC_ARM64_REG_X0, value)
                machine.reg_write(reg.UC_ARM64_REG_PC, machine.reg_read(reg.UC_ARM64_REG_X30))
                return
            assert any(lo <= pc < hi for lo, hi in code_intervals), (case['id'], 'out-of-scope code', hex(pc))
        def write(machine, access, address, size, value, unused):
            allowed = [(SAVED_SP - 0x1000, SAVED_SP), (MESSAGE + 8, MESSAGE + 16),
                       (CONTEXT + 0x29, CONTEXT + 0x2a), (RING, RING + 256)]
            assert any(lo <= address and address + size <= hi for lo, hi in allowed), (case['id'], hex(address), size)
            writes.append({'address': hex(address), 'bytes': size})
        def interrupt(machine, number, unused):
            raise AssertionError(('Guest interrupt/syscall denied', number))
        uc.hook_add(UC_HOOK_CODE, code)
        uc.hook_add(UC_HOOK_MEM_WRITE, write)
        uc.hook_add(UC_HOOK_INTR, interrupt)
        uc.emu_start(LOAD + int(request['VA'], 16), RETURN, timeout=2000000, count=5000)
        assert uc.reg_read(reg.UC_ARM64_REG_PC) == RETURN, case['id']
        returned = uc.reg_read(reg.UC_ARM64_REG_X0)
        assert returned == case['expected_return'], (case['id'], returned)
        expected_message = original_message[:8] + struct.pack('<Q', MESSAGE) + original_message[16:]
        assert bytes(uc.mem_read(MESSAGE, 64)) == expected_message
        expected_ring = bytearray(original_ring)
        if case['accepted']:
            off = case['tail'] * 64
            expected_ring[off:off + 64] = expected_message
        assert bytes(uc.mem_read(RING, 256)) == bytes(expected_ring), case['id']
        expected_context = bytearray(context_before)
        expected_context[0x29] = case['new_tail']
        assert bytes(uc.mem_read(CONTEXT, 0x200)) == bytes(expected_context)
        for address in (MESSAGE - 32, MESSAGE + 64, RING - 32, RING + 256):
            assert bytes(uc.mem_read(address, 32)) == guard
        assert uc.reg_read(reg.UC_ARM64_REG_SP) == SAVED_SP
        for n, value in saved.items():
            assert uc.reg_read(getattr(reg, 'UC_ARM64_REG_X' + str(n))) == value
        assert bytes(uc.mem_read(SAVED_SP, 32)) == bytes([0xa7]) * 32
        signal_calls = sum(x['name'] == 'pthread_cond_signal' for x in calls)
        assert signal_calls == int(case['accepted'])
        queue_calls = sum(x['name'] == '_ZN4CUsb8que_pushEPS_P8CUSB_MES' for x in calls)
        assert queue_calls == int(not case.get('lock', 0))
        results.append({'fixture': case, 'original_request_return': returned,
            'original_queue_function_entered': bool(queue_calls), 'ring_copy_observed': case['accepted'],
            'head_after': expected_context[0x28], 'tail_after': expected_context[0x29],
            'signal_calls': signal_calls, 'synthetic_external_call_returns': {k:case.get(k,0) for k in ('lock','unlock','signal')},
            'calls': calls, 'executed_instructions_and_bridge_hooks': len(executed),
            'guest_writes': writes, 'guards_callee_saved_SP_and_LR_return_verified': True})
    result = {
        'status': 'PASS_ORIGINAL_QUEUE_RETURN_COUNTEREXAMPLES_IN_DECLARED_GUEST_FIXTURES_NOT_DEVICE_EXIT',
        'execution_source_sha256': sha256(source).hexdigest(),
        'helper_source_sha256': sha256((HERE / 'audit_callback_bridge.py').read_bytes()).hexdigest(),
        'original_image_sha256': sha256(image.raw).hexdigest(),
        'original_function_pins': [{k: f[k] for k in ('name','VA','bytes','sha256')} for f in (request,queue)],
        'guest_instruction_bytes_unchanged': True,
        'PLT_bridge': 'Only original queue target redirected to its original entry; log/mutex/cond APIs are declared synthetic return fixtures.',
        'cases': results, 'case_count': len(results),
        'original_function_entries': len(results) + sum(x['original_queue_function_entered'] for x in results),
        'proved_counterexamples_within_fixture': {
            'return0_but_full_no_enqueue': ['full_but_request_returns0','wrap_full_but_request_returns0'],
            'return5_after_message_enqueued': ['unlock_failure_after_enqueue'],
            'return0_with_cond_signal_failure': ['signal_failure_after_enqueue']},
        'actual_queue_capacity_mutex_conditions_concurrent_delivery_or_USB_not_measured': True,
        'guest_original_AArch64_executed': True,
        'Sony_native_host_or_camera_code_driver_or_module_execution': False,
        'camera_or_driver_operations': 0, 'goal_complete': False, 'persistent_write_release': False}
    with (output / 'results.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'cases': len(results),
                      'original_function_entries': result['original_function_entries'],
                      'return0_without_enqueue_cases': 2, 'error_after_enqueue_cases': 1,
                      'actual_device_tests': 0}))


if __name__ == '__main__':
    main()
