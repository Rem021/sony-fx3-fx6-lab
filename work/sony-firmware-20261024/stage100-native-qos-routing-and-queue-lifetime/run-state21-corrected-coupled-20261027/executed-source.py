#!/usr/bin/env python3
"""Native timing QoS dispatch and queued-pointer lifetime, offline only.

The supplied state/timing binding is not a selected MAIN instance. Diagnostics
and state-machine delivery remain explicit gaps. No fake return, instruction
replacement, device access or deployment artifact is provided.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys
import traceback

STAGE = Path(__file__).resolve().parent
BASE = STAGE.parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(BASE / 'stage34-qos-request-and-feedback'))
import qos_paths as q
r, V, im = q.r, q.V, q.r.im
PRIOR = BASE / 'stage99-offline-cached-argument-auditor/final-receipt.json'
PRIOR_SHA = 'cd419ece663b41fd610bfce5d35bb745abeea76aff90af86f637de056ecc9c1f'
IMAGE = BASE / 'stage2/extraction/files/nflasha3/av-cam.bin'
# Full fingerprint is deliberately explicit and checked before any execution.
IMAGE_SHA = '0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'
STATE = r.ARENA + 0x10000
SM_REF = r.ARENA + 0x18000
TIMING = r.ARENA + 0x20000
INTERFACE = r.ARENA + 0x30000
CODEC = r.ARENA + 0x40000
CFG_REF = r.ARENA + 0x50000
CFG = r.ARENA + 0x51000
REQUEST = r.ARENA + 0x60000
QUEUE = STATE + 0x448
TIMING_SIZE = 0x600
LOWER_SP = r.STACK + 0x4000
BACK = r.ARENA + 0x70000
BACK_HANDLE = r.ARENA + 0x72000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def u32(raw, at=0):
    return struct.unpack_from('<I', raw, at)[0]


def u64(raw, at=0):
    return struct.unpack_from('<Q', raw, at)[0]


class Guest(r.RawGuest):
    def __init__(self, blob, seed):
        super().__init__(blob, [
            (0xa6eb0, 0xa7020), (0x1a2554, 0x1a2578),
            (0x17792c, 0x177934), (0x185024, 0x1852ac),
            (0x17b7a4, 0x17b7b4), (0x189ce8, 0x189d50),
            (0x14555c, 0x145588), (0x14670c, 0x146724),
            (0x1345e4, 0x1345ec), (0x135f28, 0x135f64),
            (0x135fd4, 0x13600c), (0xd80, 0xeec),
            (0x17df28, 0x17e044), (0x17b4d8, 0x17b520),
            (0x17effc, 0x17f244),
        ], {
            0x27d528: 'before_original_logger_getter',
            0x27d568: 'before_original_diagnostic',
            0x960a4: 'before_message_object_constructor',
            0x148a20: 'before_timing_update_helper',
            0x17effc: 'before_queued_event_state_machine',
            0x184c34: 'before_ineligible_event_handler',
            0x1849a0: 'before_nested_duplicate_event_handler',
            0x27da84: 'before_nested_event_copy_provider',
        })
        self.uc.mem_write(r.ARENA, bytes([seed]) * r.ARENA_SIZE)
        self.uc.mem_write(r.STACK, bytes([seed ^ 0x3c]) * r.STACK_SIZE)

    def phase(self, label, start, allowed=(), fresh=True, stack_ceiling=None, **registers):
        before = self.read(r.ARENA, r.ARENA_SIZE)
        stack = self.read(r.STACK, r.STACK_SIZE)
        self.reason, self.pcs, self.writes = None, [], []
        if fresh:
            self.regs(sp=r.SP, x30=r.STOP)
        self.regs(**registers)
        ceiling = r.SP if stack_ceiling is None else stack_ceiling
        floor = ceiling - 0x500
        saved = [self.uc.reg_read(getattr(r.reg, 'UC_ARM64_REG_X'+str(n))) for n in range(19,30)]
        self.uc.emu_start(V + start, 0, count=10000, timeout=1000000)
        assert self.reason is not None, 'instruction/time bound without a stop'
        after = self.read(r.ARENA, r.ARENA_SIZE)
        changed = [r.ARENA + i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        assert all(any(a <= x < z for a, z in allowed) for x in changed)
        for w in self.writes:
            at, size = int(w['address'], 16), w['size']
            assert (floor <= at and at + size <= ceiling) or any(a <= at and at + size <= z for a, z in allowed), w
        assert self.read(r.STACK, floor-r.STACK) == stack[:floor-r.STACK]
        assert self.read(ceiling, r.STACK_SIZE-(ceiling-r.STACK)) == stack[ceiling-r.STACK:]
        assert self.read(V, len(self.blob)) == self.blob
        returned_registers = None
        if fresh and self.reason == 'returned':
            returned_registers = saved == [self.uc.reg_read(getattr(r.reg, 'UC_ARM64_REG_X'+str(n))) for n in range(19,30)]
            assert returned_registers
        return {
            'label': label, 'entry': hex(V + start), 'reason': self.reason,
            'stop_pc': hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
            'SP_after': hex(self.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
            'x0_to_x5': [hex(self.uc.reg_read(getattr(r.reg, 'UC_ARM64_REG_X'+str(n)))) for n in range(6)],
            'pcs': [hex(x) for x in self.pcs], 'writes': self.writes,
            'whole_arena_outside_declared_outputs_unchanged': True,
            'stack_write_range': [hex(floor),hex(ceiling)],
            'whole_stack_outside_declared_1280_byte_range_unchanged': True,
            'callee_saved_x19_to_x29_unchanged_on_complete_independent_return': returned_registers,
            'whole_original_image_unchanged': True,
        }


def request(seed, target, update, timing):
    # All bytes are explicit fixtures. This is not an actual camera request.
    raw = bytearray((seed + i * 13) & 255 for i in range(0x4c))
    raw[4], raw[0x28], raw[0x29] = update, timing, 1
    struct.pack_into('<I', raw, 8, target)
    struct.pack_into('<I', raw, 0x48, 0x12345678)
    return bytes(raw)


def fixture(blob, seed, raw):
    m = Guest(blob, seed)
    for at, value in ((CFG_REF, CFG), (INTERFACE+0x10, CODEC), (CODEC+0x10, CFG_REF), (SM_REF, STATE)):
        m.uc.mem_write(at, r.p64(value))
    m.uc.mem_write(CFG+8, b'\x02')
    m.uc.mem_write(REQUEST, raw)
    # Actual constructor installs its own vtable; its context pointers are
    # caller-declared, and its original internal strategy is still null.
    e = m.phase('complete original timing constructor', 0xa6eb0,
                [(TIMING, TIMING+TIMING_SIZE)],
                x0=TIMING, x1=CFG_REF, x2=0, x3=0, x4=INTERFACE)
    assert e['reason'] == 'returned' and e['SP_after'] == hex(r.SP)
    assert u64(m.read(TIMING, 8)) == V+0x370c10
    assert u64(m.read(V+0x370c28, 8)) == V+0x189ce8
    assert u64(m.read(TIMING+0x18, 8)) == INTERFACE
    assert m.read(TIMING+0x278, 8) == bytes(8)
    b = m.phase('original state target binder with explicit timing argument', 0x17792c,
                [(STATE+0x20, STATE+0x28)], x0=STATE, x1=TIMING)
    assert b['reason'] == 'returned' and u64(m.read(STATE+0x20, 8)) == TIMING
    return m, [e, b]


def route_case(blob, seed, target, update, timing):
    raw = request(seed, target, update, timing)
    m, events = fixture(blob, seed, raw)
    e = m.phase('original state action through constructor-installed timing vtable',
                0x185084, x0=SM_REF, x1=REQUEST)
    events.append(e)
    assert e['reason'] == 'boundary: before_original_logger_getter'
    assert all(hex(V+x) in e['pcs'] for x in (0x17b7a4, 0x189ce8))
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X19) == REQUEST
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X20) == TIMING
    assert m.read(REQUEST, len(raw)) == raw
    pending_sp = m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    pending = m.read(pending_sp, r.SP-pending_sp)
    # Separate entry/stack: do not skip the stopped logger or fabricate its
    # return. This is the lower forwarding method, not completion of action.
    e = m.phase('independent original lower QoS forwarding and envelope copy',
                0x14555c, x0=INTERFACE, x1=REQUEST,
                sp=LOWER_SP, stack_ceiling=LOWER_SP)
    events.append(e)
    assert m.read(REQUEST, len(raw)) == raw
    assert m.read(pending_sp, r.SP-pending_sp) == pending
    if timing:
        assert e['reason'] == 'boundary: before_timing_update_helper'
        assert not any(hex(V+x) in e['pcs'] for x in (0x1345e4, 0x135f28))
        envelope = None
    else:
        assert e['reason'] == 'boundary: before_message_object_constructor'
        sp = m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
        envelope = m.read(sp+0x1a8, 0x54)
        assert envelope == struct.pack('<HHHHI', 0x2103, 0x10a, 0x54, 0, 2)+raw[:0x48]
        assert all(hex(V+x) in e['pcs'] for x in (0x1345e4, 0x135f28, 0x135fd4))
    return {'seed': seed, 'target_fixture': target, 'target_update_fixture': update,
            'timing_update_fixture': timing, 'request_hex': raw.hex(),
            'envelope_before_unexecuted_constructor_hex': envelope.hex() if envelope else None,
            'events': events, 'native_full_timing_ctor_and_binder_used': True,
            'pending_original_action_frame_preserved_by_separate_lower_stack': True,
            'actual_MAIN_binding_policy_producer_state_eligibility_or_applied_target_proven': False}


def queue_case(blob, seed, busy):
    raw = request(seed, 16000000, 1, 0)
    m, events = fixture(blob, seed, raw)
    queue = bytearray(0x20)
    struct.pack_into('<I', queue, 0, int(busy))
    if busy:
        struct.pack_into('<Q', queue, 0x10, REQUEST+0x100)
    m.uc.mem_write(QUEUE, bytes(queue))
    saved = [m.uc.reg_read(getattr(r.reg, 'UC_ARM64_REG_X'+str(n))) for n in range(19,30)]
    e = m.phase('original enqueue prologue before its first logger call', 0x17df28,
                x0=STATE, x1=REQUEST)
    events.append(e)
    assert e['reason'] == 'boundary: before_original_logger_getter'
    # Explicit post-getter entry executes original argument preparation and
    # MOV w22,1. Logger output is unused for the queue branch, but its real
    # effects and the subsequent diagnostic sequence remain unexecuted.
    e = m.phase('independent enqueue diagnostic argument prefix', 0x17df50,
                fresh=False)
    events.append(e)
    assert e['reason'] == 'boundary: before_original_diagnostic'
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X22) == 1
    e = m.phase('post-diagnostic native queue check and pointer store', 0x17dfc4,
                [(QUEUE, QUEUE+0x20)], fresh=False)
    events.append(e)
    if busy:
        assert e['reason'] == 'boundary: before_original_logger_getter'
        assert m.read(QUEUE, 0x20) == bytes(queue)
        return {'seed': seed, 'busy_fixture': True, 'events': events,
                'existing_queue_unchanged_before_busy_diagnostic': True}
    assert e['reason'] == 'returned' and e['SP_after'] == hex(r.SP)
    assert saved == [m.uc.reg_read(getattr(r.reg, 'UC_ARM64_REG_X'+str(n))) for n in range(19,30)]
    queued = m.read(QUEUE, 0x20)
    assert u32(queued) == 1 and u32(queued, 4) == u32(queued, 8) == 0
    assert u64(queued, 0x10) == REQUEST
    assert m.read(REQUEST, len(raw)) == raw
    # Explicit host trial mutation isolates pointer-versus-copy semantics.
    # It is NOT a reachable camera schedule or a firmware race allegation.
    changed = bytearray(raw); struct.pack_into('<I', changed, 8, 20000000)
    m.uc.mem_write(REQUEST, bytes(changed))
    back = bytearray(0x1000)
    struct.pack_into('<Q', back, 0, STATE)
    struct.pack_into('<I', back, 8, 3)
    m.uc.mem_write(BACK,bytes(back))
    m.uc.mem_write(BACK_HANDLE,r.p64(BACK))
    m.uc.mem_write(STATE+0x18,r.p64(BACK_HANDLE))
    e = m.phase('independent native queued-pointer pop before state delivery',
                0x17b4d8, [(QUEUE, QUEUE+0x20)], x0=STATE, x1=QUEUE)
    events.append(e)
    assert e['reason'] == 'boundary: before_queued_event_state_machine'
    ptr = m.uc.reg_read(r.reg.UC_ARM64_REG_X1)
    assert ptr == REQUEST and u32(m.read(ptr+8, 4)) == 20000000
    after = m.read(QUEUE, 0x20)
    assert u32(after) == u32(after, 8) == 0
    assert u64(after, 0x10) == REQUEST
    assert m.read(REQUEST, len(raw)) == bytes(changed)
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0) == BACK_HANDLE
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_SP) == r.SP
    del m.boundaries[V+0x17effc]
    e = m.phase('continuous popped request into original ROM-selected state3 action',
                0x17effc,[(BACK,BACK+0x1000)],fresh=False)
    events.append(e)
    assert e['reason'] == 'boundary: before_original_logger_getter'
    assert all(hex(V+x) in e['pcs'] for x in (0x185084,0x17b7a4,0x189ce8))
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X19) == REQUEST
    assert m.read(REQUEST,len(raw)) == bytes(changed)
    assert m.read(QUEUE,0x20) == after
    return {'seed': seed, 'busy_fixture': False, 'queued_before_hex': queued.hex(),
            'queued_after_pop_hex': after.hex(), 'original_request_hex': raw.hex(),
            'declared_host_mutation_hex': bytes(changed).hex(),
            'popped_pointer': hex(ptr), 'target_at_popped_pointer': 20000000,
            'stale_pointer_slot_not_erased_by_pop': True, 'events': events,
            'original_enqueue_frame_SP_and_callee_saved_x19_to_x29_restored_across_explicit_diagnostic_gaps': True,
            'popped_request_native_state_dispatch_reached_timing_logger_with_queue_already_zero': True,
            'actual_state_delivery_scheduling_or_module_lifetime_proven': False}


def event_case(blob, seed, state, active=0, pending=0):
    raw = request(seed, 16000000, 1, 0)
    m, events = fixture(blob, seed, raw)
    data = bytearray(0x1000)
    struct.pack_into('<Q', data, 0, STATE)
    struct.pack_into('<I', data, 8, state)
    data[0xc], data[0x46c] = active, pending
    m.uc.mem_write(BACK, bytes(data))
    m.uc.mem_write(BACK_HANDLE, r.p64(BACK))
    # No full back-state constructor/factory or live transition is asserted.
    # Execute the original ROM-selected event dispatch instead of supplying
    # its action function pointer or fabricating its result.
    del m.boundaries[V+0x17effc]
    e = m.phase('original QoS event dispatch using its ROM state row',
                0x17effc, [(BACK,BACK+0x1000)], x0=BACK_HANDLE, x1=REQUEST)
    events.append(e)
    assert m.read(REQUEST,len(raw)) == raw
    if state in (21,22):
        expected = 'returned'
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0) == 0
        expected_data = bytearray(data)
        struct.pack_into('<I',expected_data,8,22)
        assert m.read(BACK,len(data)) == bytes(expected_data)
    elif active:
        expected = ('boundary: before_nested_duplicate_event_handler' if pending else
                    'boundary: before_nested_event_copy_provider')
    elif state == 0:
        expected = 'boundary: before_ineligible_event_handler'
    else:
        expected = 'boundary: before_original_logger_getter'
        action = {1:0x185044,3:0x185084,8:0x18510c,18:0x18522c}[state]
        assert hex(V+action) in e['pcs']
        if state == 1:
            assert hex(V+0x17df28) in e['pcs']
            assert hex(V+0x189ce8) not in e['pcs']
        else:
            assert hex(V+0x17b7a4) in e['pcs'] and hex(V+0x189ce8) in e['pcs']
    assert e['reason'] == expected
    return {'seed':seed,'declared_numeric_state':state,'declared_active':active,
            'declared_nested_pending':pending,'events':events,
            'state_word_after':u32(m.read(BACK+8,4)),
            'active_byte_after':m.read(BACK+0xc,1)[0],
            'native_ROM_row_hex':blob[0x36c8e8+state*24:0x36c8e8+(state+1)*24].hex(),
            'normal_back_constructor_real_state_transition_or_MAIN_proven':False}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    out = Path(parser.parse_args().output).resolve()
    im.volume(); assert out.parent == STAGE and not out.exists()
    assert sha(PRIOR.read_bytes()) == PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        data = (ROOT/f['path']).read_bytes()
        assert len(data) == f['bytes'] and sha(data) == f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes() == (BASE/'GOAL_STATUS.json').read_bytes()
    blob = IMAGE.read_bytes(); assert sha(blob) == IMAGE_SHA
    out.mkdir()
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        routes = [route_case(blob, seed, target, update, timing)
                  for seed in (0xa5, 0xc3)
                  for target, update, timing in ((16000000,1,0),(20000000,1,0),(0,1,0),(16000000,0,0),(16000000,1,1))]
        queues = [queue_case(blob, seed, busy) for seed in (0xa5,0xc3) for busy in (False,True)]
        state_cases = [event_case(blob,seed,state,active,pending)
                       for seed in (0xa5,0xc3)
                       for state,active,pending in ((0,0,0),(1,0,0),(3,0,0),(8,0,0),(18,0,0),
                                                   (21,0,0),(22,0,0),(3,1,0),(3,1,1))]
        result = {
            'status': 'PASS_NATIVE_TIMING_QOS_DISPATCH_ENVELOPE_AND_BOUNDED_QUEUE_POINTER_LIFETIME',
            'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'image_sha256': sha(blob), 'previous_manifest_sha256': PRIOR_SHA,
            'unicorn_version': r.unicorn.__version__, 'capstone_version': r.capstone.__version__,
            'routes': routes, 'queues': queues, 'state_cases':state_cases,
            'bounded_phases': sum(len(c['events']) for c in routes+queues+state_cases),
            'scope': 'Complete native timing constructor, explicit original state binder, original virtual dispatch to unexecuted diagnostic. Independent lower forwarding and native pointer queue fragments with explicit diagnostic/state-machine gaps. Supplied source/request/graph/queue state are not a real MAIN, actual policy or captured camera memory.',
            'actual_MAIN_encoding_or_recovery_proven': False,
            'Windows_UU_camera_operations': False, 'goal_complete': False,
            'persistent_write_release': False,
        }
        (out/'qos-routing-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'route_cases':len(routes),'queue_cases':len(queues),'state_cases':len(state_cases),
                          'phases':result['bounded_phases'],'output':str(out)}))
    except Exception:
        (out/'attempt-failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'passing_result':False},indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
