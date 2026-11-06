#!/usr/bin/env python3
"""Consume captured original QoS prefixes with bounded original MIPS code.

Only the 64 bytes actually retained by stage78 are admitted, not an invented
full128-byte block. Stream context/handle storage is declared RAM. An existing
handle permits the original bounded update copy; missing-handle runtime state,
outer MMIO translation, allocation and hardware application stay unexecuted.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback
import unicorn as u
from unicorn import mips_const as reg
import capstone as cs

STAGE = Path(__file__).resolve().parent
BASE = STAGE.parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(BASE/'stage49-vcd-consumer-validation'))
import vcd_consumer as v
im = v.im
IMAGE = 0x80000000
INPUT_PA, INPUT = 0x01000000, 0x81000000
CTX_PA, CTX = 0x01100000, 0x81100000
STACK_PA, STACK, SP = 0x02000000, 0x82000000, 0x82008000
STOP_PA, STOP = 0x03000000, 0x83000000
HANDLE_PA, HANDLE = 0x01101000, 0x81101000
OUTPUT_PA = 0x01102000
ENTRY = 0x18fdb4
TIMING_BOUNDARY = 0x1a085c


def decode(word):
    return ((word >> 8)+1) << (6+(word & 255))


class Guest:
    def __init__(self, blob, prefix, seed):
        assert len(prefix) == 64
        self.blob, self.prefix = blob, prefix
        self.reason = None
        self.backend = False
        self.pcs, self.reads, self.stores = [], [], []
        self.uc = u.Uc(u.UC_ARCH_MIPS, u.UC_MODE_MIPS32 | u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md = cs.Cs(cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS32 | cs.CS_MODE_LITTLE_ENDIAN)
        for at, size, prot in ((0, (len(blob)+4095)&-4096, u.UC_PROT_READ | u.UC_PROT_EXEC),
                               (INPUT_PA, 4096, u.UC_PROT_READ),
                               (CTX_PA, 4096, u.UC_PROT_READ | u.UC_PROT_WRITE),
                               (STACK_PA, 0x10000, u.UC_PROT_READ | u.UC_PROT_WRITE),
                               (STOP_PA, 4096, u.UC_PROT_READ | u.UC_PROT_EXEC)):
            self.uc.mem_map(at, size, prot)
        self.uc.mem_write(0, blob)
        self.uc.mem_write(INPUT_PA, prefix)
        self.uc.mem_write(STACK_PA, bytes([0xd7])*0x10000)
        context = bytearray([seed])*0x400
        context[1] = 0  # Declared no-pending-update input, not actual state.
        context[0x15] = 0  # Declared stream-kind branch input.
        struct.pack_into('<I', context, 0x198, ((16000000//64)-1) << 8)
        old_flags = int.from_bytes(bytes([seed])*4, 'little') & ~0x20000000
        struct.pack_into('<I', context, 0x280, old_flags)
        self.context_before = bytes(context)
        self.uc.mem_write(CTX_PA, self.context_before)
        self.uc.reg_write(reg.UC_MIPS_REG_SP, SP)
        self.uc.reg_write(reg.UC_MIPS_REG_RA, STOP)
        self.uc.reg_write(reg.UC_MIPS_REG_A0, CTX)
        self.uc.reg_write(reg.UC_MIPS_REG_A1, INPUT)
        self.uc.reg_write(reg.UC_MIPS_REG_A2, CTX+0x108)
        self.saved = {}
        for i in range(6):
            at = getattr(reg, 'UC_MIPS_REG_S'+str(i))
            value = 0x12121212+i
            self.saved[at] = value
            self.uc.reg_write(at, value)
        self.uc.hook_add(u.UC_HOOK_CODE, self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_READ, self.load)
        self.uc.hook_add(u.UC_HOOK_MEM_WRITE, self.store)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID, self.invalid)

    def stop(self, reason):
        self.reason = reason
        self.uc.emu_stop()

    def code(self, uc, pc, size, user):
        self.pcs.append(pc)
        if pc == STOP:
            return self.stop('returned')
        if pc == IMAGE+TIMING_BOUNDARY:
            return self.stop('boundary: original_timing_helper_before_execution')
        if self.backend and pc == IMAGE+0x19bdd8:
            return self.stop('boundary: original_runtime_GP_dependency_before_execution')
        off = pc-IMAGE
        spans = [(0x18fdb4, 0x190050), (0x18faa0, 0x18fb34)]
        if self.backend:
            spans.append((0x19bda4, 0x19bf68))
        assert any(a <= off and off+size <= z for a, z in spans)
        raw = bytes(uc.mem_read(off, size))
        assert raw == self.blob[off:off+size]
        ins = next(self.md.disasm(raw, pc), None)
        assert ins is not None and ins.mnemonic not in {
            'syscall', 'break', 'cache', 'sync', 'mfc0', 'mtc0', 'eret',
            'wait', 'tlbwi', 'tlbwr', 'tlbr', 'tlbp'}

    def load(self, uc, access, at, size, value, user):
        spans = [
            (0, len(self.blob)), (INPUT_PA, INPUT_PA+len(self.prefix)),
            (CTX_PA, CTX_PA+0x400), (STACK_PA, STACK_PA+0x10000)]
        if self.backend:
            spans.extend(((HANDLE_PA, HANDLE_PA+4), (OUTPUT_PA, OUTPUT_PA+0x400)))
        assert any(a <= at and at+size <= z for a, z in spans)
        self.reads.append({'pc': hex(uc.reg_read(reg.UC_MIPS_REG_PC)), 'physical_address': hex(at), 'bytes': size})

    def store(self, uc, access, at, size, value, user):
        if self.backend:
            allowed = ((CTX_PA+0x130, CTX_PA+0x134), (OUTPUT_PA+0x1c, OUTPUT_PA+0x140),
                       (STACK_PA, STACK_PA+0x10000))
        else:
            allowed = ((CTX_PA+1, CTX_PA+2), (CTX_PA+0x198, CTX_PA+0x19c),
                       (CTX_PA+0x280, CTX_PA+0x284), (STACK_PA, STACK_PA+0x10000))
        assert any(a <= at and at+size <= z for a, z in allowed), (hex(at), size)
        self.stores.append({'pc': hex(uc.reg_read(reg.UC_MIPS_REG_PC)), 'physical_address': hex(at),
                            'bytes': size, 'value_low_bits': hex(value & ((1 << (size*8))-1))})

    def invalid(self, uc, access, at, size, value, user):
        self.stop('invalid guest memory '+hex(at))
        return False

    def run(self, label):
        self.uc.emu_start(IMAGE+ENTRY, 0, count=20000, timeout=1000000)
        assert self.reason in ('returned', 'boundary: original_timing_helper_before_execution'), self.reason
        assert bytes(self.uc.mem_read(0, len(self.blob))) == self.blob
        assert bytes(self.uc.mem_read(INPUT_PA, len(self.prefix))) == self.prefix
        after = bytes(self.uc.mem_read(CTX_PA, 0x400))
        mask = struct.unpack_from('<I', self.prefix)[0]
        expected = bytearray(self.context_before)
        if mask & 0x80:
            expected[1] = 1
            expected[0x198:0x19c] = self.prefix[0x18:0x1c]
            flags = struct.unpack_from('<I', expected, 0x280)[0] | 0x20000000
            struct.pack_into('<I', expected, 0x280, flags)
        assert after == bytes(expected)
        if self.reason == 'returned':
            assert self.uc.reg_read(reg.UC_MIPS_REG_SP) == SP
            assert all(self.uc.reg_read(at) == value for at, value in self.saved.items())
        timing = None
        if mask & 0x100:
            assert self.reason == 'boundary: original_timing_helper_before_execution'
            a0, a1 = self.uc.reg_read(reg.UC_MIPS_REG_A0), self.uc.reg_read(reg.UC_MIPS_REG_A1)
            assert a0 == CTX+0x108 and STACK <= a1 < STACK+0x10000
            raw = bytes(self.uc.mem_read(a1-IMAGE, 8))
            assert raw == struct.pack('<IHBB', 240000, 8008, 0, 0)
            timing = {'a0': hex(a0), 'a1': hex(a1), 'original_stack_argument8_hex': raw.hex(), 'callee_executed': False}
        offsets = set()
        for row in self.reads:
            at = int(row['physical_address'], 16)
            offsets.update(range(max(at, INPUT_PA)-INPUT_PA, min(at+row['bytes'], INPUT_PA+64)-INPUT_PA))
        return {
            'label': label, 'reason': self.reason, 'pc': hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
            'input_prefix64_hex': self.prefix.hex(), 'input_offsets_read': sorted(offsets),
            'context_before_hex': self.context_before.hex(), 'context_after_hex': after.hex(),
            'decoded_context_target_before': decode(struct.unpack_from('<I', self.context_before, 0x198)[0]),
            'decoded_context_target_after': decode(struct.unpack_from('<I', after, 0x198)[0]),
            'pending_byte_after': after[1], 'timing_boundary': timing,
            'pcs': [hex(x) for x in self.pcs], 'reads': self.reads, 'stores': self.stores,
            'original_image_and_input_unchanged': True,
            'whole_context_matches_only_declared_target_flag_and_pending_changes': True,
            'scalar_return_not_used_as_hardware_success': True,
            'outer_MMIO_translation_allocator_or_hardware_application_executed': False,
        }

    def transfer(self, present):
        """Independent original update entry with explicit handle/no-handle."""
        assert self.reason == 'returned'
        self.backend = True
        for at, prot in ((HANDLE_PA, u.UC_PROT_READ), (OUTPUT_PA, u.UC_PROT_READ | u.UC_PROT_WRITE)):
            self.uc.mem_map(at, 4096, prot)
        self.uc.mem_write(HANDLE_PA, struct.pack('<I', OUTPUT_PA))
        self.uc.mem_write(OUTPUT_PA, bytes([0xb6])*0x400)
        self.uc.mem_write(CTX_PA+0x10c, struct.pack('<I', HANDLE if present else 0))
        flags = struct.unpack('<I', bytes(self.uc.mem_read(CTX_PA+0x130, 4)))[0] & ~0x40
        self.uc.mem_write(CTX_PA+0x130, struct.pack('<I', flags))
        before = bytes(self.uc.mem_read(CTX_PA, 0x400))
        source = before[0x18c:0x18c+0x124]
        self.reason = None
        self.pcs, self.reads, self.stores = [], [], []
        self.uc.reg_write(reg.UC_MIPS_REG_SP, SP)
        self.uc.reg_write(reg.UC_MIPS_REG_RA, STOP)
        self.uc.reg_write(reg.UC_MIPS_REG_A0, CTX+0x108)
        self.uc.reg_write(reg.UC_MIPS_REG_A1, CTX+0x18c)
        self.uc.emu_start(IMAGE+0x19bda4, 0, count=20000, timeout=1000000)
        expected = bytearray(before)
        output = bytes(self.uc.mem_read(OUTPUT_PA, 0x400))
        if present:
            assert self.reason == 'returned'
            assert self.uc.reg_read(reg.UC_MIPS_REG_SP) == SP
            assert all(self.uc.reg_read(at) == value for at, value in self.saved.items())
            assert output[:0x1c] == bytes([0xb6])*0x1c
            assert output[0x1c:0x140] == source and output[0x140:] == bytes([0xb6])*(0x400-0x140)
            struct.pack_into('<I', expected, 0x130, flags | 0x40)
        else:
            assert self.reason == 'boundary: original_runtime_GP_dependency_before_execution'
            assert output == bytes([0xb6])*0x400
        after = bytes(self.uc.mem_read(CTX_PA, 0x400))
        assert after == bytes(expected)
        assert bytes(self.uc.mem_read(0, len(self.blob))) == self.blob
        assert bytes(self.uc.mem_read(INPUT_PA, len(self.prefix))) == self.prefix
        return {
            'declared_existing_handle': present, 'reason': self.reason,
            'original_parameter_source292_hex': source.hex(),
            'output_guarded1024_hex': output.hex(),
            'native_copy_bytes': 292 if present else 0,
            'copied_target_decoded': decode(struct.unpack_from('<I', output, 0x28)[0]) if present else None,
            'backend_update_flag_after': struct.unpack_from('<I', after, 0x130)[0],
            'pending_byte_not_cleared': after[1] == before[1] == 1,
            'context_matches_only_backend_update_flag_change': True,
            'pcs': [hex(x) for x in self.pcs], 'reads': self.reads, 'stores': self.stores,
            'allocation_GP_path_hardware_application_or_upper_completion_executed': False,
            'handle_and_physical_buffer_are_declared_fixtures_not_actual_allocations': True,
        }


def run(out):
    prior = BASE/'stage78-native-start-flags-and-query-tail/final-receipt.json'
    assert im.sha(prior.read_bytes()) == 'abe85ad128853086e4af536afdd72050aa18d5713e3a7ce3f8c0943ee8e820b5'
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes()) == row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes() == (STAGE/'goal-status-before.json').read_bytes()
    original_result = prior.parent/'run-20261026/start-flags-results.json'
    captured = json.loads(original_result.read_text())
    blob = v.VCD_PATH.read_bytes()
    assert im.sha(blob) == im.PINS[str(v.VCD_PATH.relative_to(BASE))]
    cases = []
    for source in captured['cases']:
        for index in (0, 1, 2, 3):
            prefix = bytes.fromhex(source['cases'][index]['extra_first64_hex'])
            m = Guest(blob, prefix, source['seed'])
            global CURRENT_GUEST
            CURRENT_GUEST = m
            e = m.run(source['cases'][index]['label'])
            e.update(seed=source['seed'], source_case_index=index, source_bytes_unmodified=True)
            if index in (1, 2):
                e['independent_existing_handle_transfer'] = m.transfer(True)
            cases.append(e)
        # A fresh declared no-handle input stops before reading unknown runtime
        # GP state. It is never assigned a fake allocator or service return.
        prefix = bytes.fromhex(source['cases'][2]['extra_first64_hex'])
        m = Guest(blob, prefix, source['seed'])
        CURRENT_GUEST = m
        e = m.run('target20M with independently declared missing backend handle')
        e.update(seed=source['seed'], source_case_index=2, source_bytes_unmodified=True)
        e['independent_missing_handle_boundary'] = m.transfer(False)
        cases.append(e)
        prefix = bytearray.fromhex(source['cases'][2]['extra_first64_hex'])
        struct.pack_into('<I', prefix, 0, 0)
        m = Guest(blob, bytes(prefix), source['seed'])
        CURRENT_GUEST = m
        e = m.run('control: retained20M word with update mask cleared')
        assert e['decoded_context_target_after'] == 16000000 and e['pending_byte_after'] == 0
        e.update(seed=source['seed'], source_case_index=2, source_bytes_unmodified=False,
                 declared_mutation='Only4-byte update mask set to0; explicit negative control, not device modification.')
        cases.append(e)
    result = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'PASS_ORIGINAL_MIPS_QOS_TARGET_CONSUMER_WITH_BOUNDED_TIMING_STOP',
        'cases': cases, 'original_returned_cases': sum(x['reason']=='returned' for x in cases),
        'timing_boundary_cases': sum(x['reason']!='returned' for x in cases),
        'independent_existing_handle_transfers': sum('independent_existing_handle_transfer' in x for x in cases),
        'independent_missing_handle_boundaries': sum('independent_missing_handle_boundary' in x for x in cases),
        'original_function_entries': len(cases)+sum(
            'independent_existing_handle_transfer' in x or 'independent_missing_handle_boundary' in x for x in cases),
        'source_receipt': {'script_sha256': im.sha(Path(__file__).read_bytes()),
                           'captured_stage78_result_sha256': im.sha(original_result.read_bytes()),
                           'VCD_sha256': im.sha(blob)},
        'original_regions': [{'start': hex(a), 'end': hex(z), 'instructions': v.mips_dump(blob, a, z)}
                             for a, z in ((0x18faa0, 0x18fb34), (0x18fd58, 0x190050),
                                          (0x190444, 0x1904f4), (0x190878, 0x190904))],
        'runtime_update_words': [
            {'offset': hex(at), 'bytes': blob[at:at+4].hex(),
             'asm': next((i.mnemonic+' '+i.op_str for i in cs.Cs(
                 cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS32 | cs.CS_MODE_LITTLE_ENDIAN).disasm(
                     blob[at:at+4], IMAGE+at)), None)}
            for at in range(0x19bda4, 0x19bf68, 4)],
        'scope': [
            'Original stage78 QoS prefixes are consumed by original MIPS18fdb4/18faa0 with declared RAM context.',
            'Enabled target writes context198, marks context280 bit29 and pending byte1; cleared mask leaves16M despite retained20M data.',
            'Timing case passes the original query-derived8-byte argument then stops before1a085c. No timing helper return is supplied.',
            'Only retained64-byte prefixes admitted. Not a full128-byte physical transfer or actual whole-stream initial state.',
            'Independent existing-handle19bda4 copies292 bytes including target to a declared buffer, sets backend flag and leaves outer pending byte. No real allocation/physical map/upper completion is proven.',
            'Independent missing-handle19bda4 stops before GP load; allocator/runtime branch and unknown instruction encodings remain unexecuted.',
            'Outer MMIO translation18fd58, complete Start, encoder/hardware application, output bitstream and recovery are unexecuted.'],
        'Windows_UU_camera_operations': False, 'goal_complete': False, 'persistent_write_release': False,
    }
    im.write_json(out/'vcd-qos-results.json', result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status': result['status'], 'cases': len(cases),
                      'returned': result['original_returned_cases'], 'bounded_timing_stops': result['timing_boundary_cases'],
                      'existing_handle_copies': result['independent_existing_handle_transfers'],
                      'missing_handle_boundaries': result['independent_missing_handle_boundaries'],
                      'actual_hardware_application_proven': False}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    im.volume()
    out = Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    try:
        run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json', {'traceback': traceback.format_exc(), 'passing_result': False})
        if 'CURRENT_GUEST' in globals():
            m = CURRENT_GUEST
            im.write_json(out/'failure-state.json', {'pc': hex(m.uc.reg_read(reg.UC_MIPS_REG_PC)),
                                                    'reason': m.reason, 'last_pcs': [hex(x) for x in m.pcs[-12:]]})
        raise


if __name__ == '__main__':
    main()
