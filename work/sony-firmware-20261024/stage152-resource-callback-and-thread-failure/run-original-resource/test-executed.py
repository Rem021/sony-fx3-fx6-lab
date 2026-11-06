#!/usr/bin/env python3
"""Bounded original MWF/Obj call flow; all OS/message/loader effects are fixtures."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_INTR
from unicorn import arm64_const as R

HERE = Path(__file__).resolve().parent
O, M, D, S, RET = 0x10000000, 0x30000000, 0x40000000, 0x50000000, 0x60000000
SP = S + 0xf000
CONTEXT, RSRC, SEED, QUEUED, PAYLOAD, LIST, KEY, COUNT = [D + n * 0x100 for n in range(1, 9)]
TOKEN, PAYLOAD_TOKEN = 0x7131, 0x7141


def load():
    path = HERE / 'original_resource.py'
    assert path.read_bytes() == (HERE / 'static-executed.py').read_bytes()
    spec = importlib.util.spec_from_file_location('reviewed_resource_originals', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Guest:
    def __init__(self, source, static, options):
        self.options = options
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        unused, obj, mwf = source.images()
        self.ranges, self.plts, self.entry_names, self.snapshots = [], {}, {}, []
        for base, image, functions in [(O, obj, static['object_functions']), (M, mwf, static['middleware_functions'])]:
            pages = sorted({p for seg in image.loads for p in range((base + seg['p_vaddr']) & ~0xfff,
                (base + seg['p_vaddr'] + seg['p_memsz'] + 0xfff) & ~0xfff, 0x1000)})
            for page in pages:
                self.uc.mem_map(page, 0x1000)
            for segment in image.loads:
                self.uc.mem_write(base + segment['p_vaddr'], segment.data())
            for f in functions:
                start = int(f['VA'], 16)
                assert sha256(image.read(start, f['bytes'])).hexdigest() == f['sha256']
                self.ranges.append((base + start, base + start + f['bytes']))
                self.entry_names[base + start] = ('Obj' if base == O else 'MWF') + ':' + f['VA']
            self.plts.update({base + address: name for address, name in image.plt.items()})
        for offset, value in static['selected_relative_relocations'].items():
            self.uc.mem_write(O + int(offset, 16), struct.pack('<Q', O + int(value, 16)))
        self.uc.mem_map(D, 0x10000)
        self.uc.mem_map(S, 0x10000)
        self.uc.mem_map(RET, 0x1000)
        self.uc.mem_write(S, bytes([0xa7]) * 0x10000)
        self.uc.mem_write(QUEUED, struct.pack('<QQ', TOKEN, 0))
        self.uc.mem_write(PAYLOAD, struct.pack('<QQ', PAYLOAD_TOKEN, 0))
        self.uc.mem_write(KEY, struct.pack('<Q', 42))
        self.uc.mem_write(COUNT, struct.pack('<Q', options.get('pending', 1)))
        self.uc.mem_write(LIST + 0x18, struct.pack('<I', 1))
        self.allocations = 0
        self.report = {'options': options, 'original_entries': [], 'bridges': [], 'writes': 0, 'thread_create_calls': [],
            'cancel_calls': [], 'join_calls': [], 'dlclose_calls': [], 'sem_post_calls': [], 'sem_init_calls': [],
            'callback_dispatches': 0, 'sub_add_user_list_calls': 0, 'invocations': []}
        self.checkpoint = None
        self.snapshots = [(a, bytes(self.uc.mem_read(a, b - a))) for a, b in self.ranges]
        self.uc.hook_add(UC_HOOK_CODE, self.code)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self.on_write)
        self.uc.hook_add(UC_HOOK_INTR, self.interrupt)

    def reg(self, n):
        return self.uc.reg_read(getattr(R, 'UC_ARM64_REG_X' + str(n)))

    def u64(self, address):
        return struct.unpack('<Q', bytes(self.uc.mem_read(address, 8)))[0]

    def u32(self, address):
        return struct.unpack('<I', bytes(self.uc.mem_read(address, 4)))[0]

    def write(self, address, data, original=False):
        valid = (D <= address and address + len(data) <= D + 0x10000) or \
            (S <= address and address + len(data) <= SP) or \
            (O + 0x2ce0ac <= address and address + len(data) <= O + 0x2ce0f0) or \
            (O + 0x2ce108 <= address and address + len(data) <= O + 0x2ce170)
        assert valid, ('write outside reviewed fixture storage', hex(address), len(data))
        self.report['writes'] += 1
        if not original:
            self.uc.mem_write(address, data)

    def on_write(self, unused, access, address, size, value, extra):
        self.write(address, bytes(size), original=True)

    def interrupt(self, unused, number, extra):
        raise AssertionError(('guest syscall/interrupt denied', number))

    def returned(self, value):
        self.uc.reg_write(R.UC_ARM64_REG_X0, value & 0xffffffffffffffff)
        self.uc.reg_write(R.UC_ARM64_REG_PC, self.reg(30))

    def code(self, unused, pc, size, extra):
        if pc == RET:
            return
        if pc in self.entry_names:
            self.report['original_entries'].append(self.entry_names[pc])
        if pc == O + 0xea9b4:
            self.report['callback_dispatches'] += 1
        if pc == O + 0xea8d4:
            self.checkpoint = 'BEFORE_SECOND_SEM_WAIT_WITH_INTERNAL_STATE4'
            self.uc.emu_stop()
            return
        if pc in [O + 0xea070, O + 0xea2b0, O + 0xea3a0]:
            self.report['bridges'].append('CPU_fixture_local_logging')
            self.returned(0)
            return
        if pc not in self.plts:
            assert any(a <= pc < b for a, b in self.ranges), ('unreviewed original instruction', hex(pc))
            return
        name = self.plts[pc]
        native = {
            '_ZN3MWF8RsrcAcsr13LibGetAcsrMsgENS_6ObjMsgEPPS1_PjS4_': M + 0x36d78,
            '_ZN3MWF8RsrcAcsr11SubCallbackENS_6ObjMsgE': M + 0x3808c,
            '_ZNK3MWF17ParamStd_TemplateIjLNS_5Param4TypeE8EE8GetValueEv': M + 0x2f420,
            '_ZN3MWF17ParamStd_TemplateIjLNS_5Param4TypeE8EE8SetValueEj': M + 0x2f3c0}
        if name in native:
            self.uc.reg_write(R.UC_ARM64_REG_PC, native[name])
            return
        a = [self.reg(n) for n in range(6)]
        self.report['bridges'].append(name)
        if name == '_Znwm':
            assert (self.allocations, a[0]) in [(0, 0x48), (1, 0x10)]
            answer = [RSRC, SEED][self.allocations]
            self.allocations += 1
        elif name == '_ZN3MWF8RsrcAcsrC1EN7DefRsrc8AcsrId_tEPvPFvS3_NS_6ObjMsgEEj':
            assert a[:5] == [RSRC, 0x2a, CONTEXT, O + 0xea9b4, 0x3d]
            self.write(RSRC, bytes(0x48))
            self.write(RSRC + 0x10, struct.pack('<QQ', a[2], a[3]))
            answer = 0
        elif name == '_ZN3MWF6ObjMsgC1Ev':
            self.write(a[0], bytes(16))
            answer = 0
        elif name == '_ZN3MWF6ObjMsgC1ERKS0_':
            assert self.u64(a[1]) in (TOKEN, PAYLOAD_TOKEN)
            self.write(a[0], bytes(self.uc.mem_read(a[1], 16)))
            answer = 0
        elif name == '_ZN3MWF6ObjMsgD1Ev':
            answer = 0  # Declared token-copy fixtures, no actual ObjMsg refcount ABI claim.
        elif name == '_ZN3MWF10ObjMsgList6GetMsgEi':
            assert a[:2] == [LIST, 0]
            answer = QUEUED
        elif name == '_ZNK3MWF6ObjMsg8GetParamEj':
            assert self.u64(a[0]) == TOKEN
            assert a[1] in (0x1000, 0x1001, 0x1002)
            answer = {0x1000: 0 if self.options.get('null_payload') else PAYLOAD, 0x1001: KEY, 0x1002: COUNT}[a[1]]
        elif name == '_ZN3MWF10ObjMsgList8pop_headEPNS_6ObjMsgE':
            assert a[0] == LIST and self.u32(LIST + 0x18) == 1
            self.write(a[1], bytes(self.uc.mem_read(QUEUED, 16)))
            self.write(LIST + 0x18, struct.pack('<I', 0))
            answer = 0
        elif name == '_ZN3MWF8RsrcAcsr14SubAddUserListENS_6ObjMsgEj':
            assert a[0] == RSRC and self.u64(a[1]) == TOKEN and a[2] == 42
            self.report['sub_add_user_list_calls'] += 1
            answer = self.options.get('sub_add', 0)
        elif name == '_ZN3MWF10ObjMsgListC1Ev':
            self.write(a[0], bytes(32))
            answer = 0
        elif name == '_ZN3MWF8RsrcAcsr24SubCheckRsrcMgrLIFOExistEPNS_10ObjMsgListE':
            assert a[0] == RSRC and self.u32(a[1] + 0x18) == 0
            answer = 0
        elif name in ['_ZN3MWF10ObjMsgListD1Ev', '_ZN3MWF8MyPrintfENS_6RsrcDP2PLEPKcz', 'pthread_attr_init', 'pthread_attr_setdetachstate']:
            answer = 0
        elif name == 'pthread_create':
            resource = self.reg(30) == O + 0xea980
            assert a[2] == (O + 0xea750 if resource else O + 0xea1dc)
            assert a[3] == 0
            result = self.options.get('resource_create' if resource else 'main_create', 0)
            self.report['thread_create_calls'].append({'kind': 'resource' if resource else 'normal', 'result_fixture': result, 'entry': hex(a[2])})
            if result == 0:
                self.write(a[0], struct.pack('<Q', 0x81 if resource else 0x88))
            answer = result
        elif name == 'sem_post':
            assert a[0] == O + 0x2ce0e0
            answer = self.options.get('sem_post', 0)
            self.report['sem_post_calls'].append(answer)
        elif name == '_Z19SenserIfRegSenEndCBPv':
            assert a[0] == O + 0xeac50
            answer = 0
        elif name == 'sem_init':
            assert a[0] in [O + 0x2ce0e0, O + 0x2ce0b8] and a[1:3] == [0, 0]
            answer = -1 if self.options.get('sem_init_fail') == len(self.report['sem_init_calls']) + 1 else 0
            self.report['sem_init_calls'].append(answer)
        elif name == 'sem_wait':
            assert a[0] == O + 0x2ce0e0
            answer = 0
        elif name == 'sem_destroy':
            assert a[0] in [O + 0x2ce0e0, O + 0x2ce0b8]
            answer = 0
        elif name in ['pthread_mutex_lock', 'pthread_mutex_unlock']:
            assert a[0] == O + 0x2ce118
            answer = 0
        elif name == 'pthread_cancel':
            assert a[0] == 0x71
            answer = self.options.get('cancel', 0)
            self.report['cancel_calls'].append(answer)
        elif name == 'pthread_join':
            assert a[:2] == [0x71, 0]
            answer = self.options.get('join', 0)
            self.report['join_calls'].append(answer)
        elif name == 'dlclose':
            assert a[0] == 0x91
            answer = self.options.get('dlclose', 0)
            self.report['dlclose_calls'].append(answer)
        elif name == 'pthread_exit':
            self.checkpoint = 'AT_PTHREAD_EXIT_FIXTURE_BOUNDARY_NOT_REAL_THREAD_EXIT'
            self.uc.emu_stop()
            return
        else:
            raise AssertionError(('unreviewed bridge', name, hex(pc)))
        self.returned(answer)

    def invoke(self, entry, args):
        self.checkpoint = None
        self.uc.reg_write(R.UC_ARM64_REG_SP, SP)
        self.uc.reg_write(R.UC_ARM64_REG_X30, RET)
        for n in range(8):
            self.uc.reg_write(getattr(R, 'UC_ARM64_REG_X' + str(n)), args[n] if n < len(args) else 0)
        try:
            self.uc.emu_start(entry, RET, timeout=3000000, count=100000)
        except Exception as error:
            raise AssertionError({'pc': hex(self.uc.reg_read(R.UC_ARM64_REG_PC)), 'entry': hex(entry),
                'recent_entries': self.report['original_entries'][-6:], 'bridges': self.report['bridges'][-5:]}) from error
        if self.checkpoint is None:
            assert self.uc.reg_read(R.UC_ARM64_REG_PC) == RET
            assert self.uc.reg_read(R.UC_ARM64_REG_SP) == SP
        assert bytes(self.uc.mem_read(SP, 32)) == bytes([0xa7]) * 32
        for address, data in self.snapshots:
            assert bytes(self.uc.mem_read(address, len(data))) == data
        result = {'entry': hex(entry), 'return_low32': self.reg(0) & 0xffffffff, 'checkpoint': self.checkpoint}
        self.report['invocations'].append(result)
        return result


def callback_case(source, static, options):
    g = Guest(source, static, options)
    g.invoke(O + 0xea58c, [CONTEXT, options.get('mode', 0)])
    assert g.u64(CONTEXT) == RSRC and g.u64(CONTEXT + 8) == SEED
    for iteration in range(2 if options.get('repeat') else 1):
        if iteration:
            g.write(COUNT, struct.pack('<Q', 1))
            g.write(LIST + 0x18, struct.pack('<I', 1))
        result = g.invoke(M + 0x38238, [RSRC, options.get('incoming_key', 42), LIST])
    g.report.update({'pending_after': g.u64(COUNT), 'resource_thread_flag_after': bytes(g.uc.mem_read(O + 0x2ce0d9, 1))[0],
        'last_return_low32': result['return_low32'], 'original_code_unchanged_and_entry_stack_guard_preserved': True})
    return g.report


def worker_case(source, static, options):
    g = Guest(source, static, options)
    g.write(O + 0x2ce0ac, struct.pack('<I', 2))
    g.write(O + 0x2ce0d9, b'\1')
    g.write(O + 0x2ce148, struct.pack('<Q', 0x91))
    g.write(O + 0x2ce150, struct.pack('<Q', 0x71))
    g.write(O + 0x2ce158, bytes([options.get('loaded', 0)]))
    g.write(O + 0x2ce160, struct.pack('<Q', 0xffffffffffffffff))
    result = g.invoke(O + 0xea750, [0])
    g.report.update({'internal_state_after': g.u32(O + 0x2ce0ac), 'old_thread_token_after': hex(g.u64(O + 0x2ce150)),
        'loader_token_after': hex(g.u64(O + 0x2ce148)), 'resource_thread_flag_after': bytes(g.uc.mem_read(O + 0x2ce0d9, 1))[0],
        'checkpoint': result['checkpoint'], 'original_code_unchanged_and_entry_stack_guard_preserved': True})
    return g.report


def main():
    source = load()
    static = json.loads((HERE / 'original-resource-static.json').read_text())
    callbacks = [callback_case(source, static, options) for options in [
        {'name': 'matched_pending1'}, {'name': 'resource_create_failure_then_repeat', 'resource_create': 11, 'repeat': True, 'sem_post': 22},
        {'name': 'key_mismatch', 'incoming_key': 41}, {'name': 'pending2', 'pending': 2}, {'name': 'pending0', 'pending': 0},
        {'name': 'null_payload', 'null_payload': True}, {'name': 'mode_field1', 'mode': 1}, {'name': 'sub_add_failure', 'sub_add': 7}]]
    workers = [worker_case(source, static, options) for options in [
        {'name': 'join_success'}, {'name': 'cancel_join_failure', 'cancel': 3, 'join': 3},
        {'name': 'join_and_dlclose_failure_loaded_control', 'join': 3, 'loaded': 1, 'dlclose': -1},
        {'name': 'normal_create_failure', 'main_create': 11}, {'name': 'first_sem_init_failure', 'sem_init_fail': 1},
        {'name': 'second_sem_init_failure', 'sem_init_fail': 2}]]
    assert callbacks[0]['pending_after'] == 0 and callbacks[0]['callback_dispatches'] == 1 and callbacks[0]['last_return_low32'] == 0
    failure = callbacks[1]
    assert failure['callback_dispatches'] == 2 and failure['resource_thread_flag_after'] == 1
    assert failure['thread_create_calls'] == [{'kind': 'resource', 'result_fixture': 11, 'entry': hex(O + 0xea750)}]
    assert failure['sem_post_calls'] == [22] and failure['sem_init_calls'] == [] and failure['last_return_low32'] == 0
    assert callbacks[2]['pending_after'] == 1 and callbacks[2]['callback_dispatches'] == 0
    assert callbacks[3]['pending_after'] == 1 and callbacks[3]['callback_dispatches'] == 0
    assert callbacks[4]['last_return_low32'] == 1 and callbacks[4]['callback_dispatches'] == 0
    assert callbacks[5]['last_return_low32'] == 1 and callbacks[5]['callback_dispatches'] == 0
    assert callbacks[6]['callback_dispatches'] == 1 and callbacks[6]['thread_create_calls'] == [] and callbacks[6]['resource_thread_flag_after'] == 0
    assert callbacks[7]['last_return_low32'] == 7 and callbacks[7]['callback_dispatches'] == 0
    for w in workers[:3]:
        assert w['internal_state_after'] == 4 and w['checkpoint'] == 'BEFORE_SECOND_SEM_WAIT_WITH_INTERNAL_STATE4'
    assert workers[0]['old_thread_token_after'] == '0xffffffffffffffff'
    assert workers[1]['old_thread_token_after'] == '0x71' and workers[1]['join_calls'] == [3]
    assert workers[2]['old_thread_token_after'] == '0x71' and workers[2]['dlclose_calls'] == [-1] and workers[2]['loader_token_after'] == '0x0'
    for w in workers[3:]:
        assert w['internal_state_after'] == 0 and w['resource_thread_flag_after'] == 0
        assert w['checkpoint'] == 'AT_PTHREAD_EXIT_FIXTURE_BOUNDARY_NOT_REAL_THREAD_EXIT'
    output = HERE / 'run-original-resource'
    output.mkdir(exist_ok=False)
    (output / 'test-executed.py').write_bytes(Path(__file__).read_bytes())
    (output / 'source-executed.py').write_bytes((HERE / 'original_resource.py').read_bytes())
    report = {'status': 'PASS_ORIGINAL_RESOURCE_AND_WORKER_FAILURE_FLOW_NOT_ACTUAL_OS_OR_CAMERA_COMPLETION',
        'callback_cases': callbacks, 'worker_cases': workers, 'case_count': len(callbacks) + len(workers),
        'original_function_entries': sum(len(c['original_entries']) for c in callbacks + workers),
        'real_queue_delivery_thread_exit_dlclose_or_mode_transition_proven': False,
        'actual_initial_MSC_auth_or_runtime_registration_proven': False,
        'message_copy_list_management_OS_thread_semaphore_loader_and_log_calls_use_declared_fixtures': True,
        'new_device_Windows_USB_operations': 0, 'test_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    with (output / 'results.json').open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': report['status'], 'cases': report['case_count'], 'original_function_entries': report['original_function_entries'], 'new_device_operations': 0}))


if __name__ == '__main__':
    main()
