#!/usr/bin/env python3
"""Original QoS/timing copy and upper pending drain, declared RAM only.

Full original QoS dispatch may run through original timing copy when a backend
handle is explicitly supplied. An independent upper fragment naturally calls
the existing-handle parameter updater and stops before its outer epilogue.
No allocator, GP state, MMIO, hardware acknowledgement or completion is faked.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE = Path(__file__).resolve().parent
BASE = STAGE.parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(BASE/'stage79-vcd-qos-consumption'))
import vcd_qos as a
im, u, reg, cs = a.im, a.u, a.reg, a.cs
IMAGE, INPUT_PA, CTX_PA, CTX = a.IMAGE, a.INPUT_PA, a.CTX_PA, a.CTX
HANDLE_PA, HANDLE, OUTPUT_PA = a.HANDLE_PA, a.HANDLE, a.OUTPUT_PA
SP, STACK_PA, STACK, STOP = a.SP, a.STACK_PA, a.STACK, a.STOP
UPPER_SP = STACK+0x6000


class Guest(a.Guest):
    def __init__(self, blob, prefix, seed, handle):
        super().__init__(blob, prefix, seed)
        self.handle_present = handle
        self.mode = 'qos'
        self.entries = []
        self.uc.mem_map(HANDLE_PA, 4096, u.UC_PROT_READ)
        self.uc.mem_map(OUTPUT_PA, 4096, u.UC_PROT_READ | u.UC_PROT_WRITE)
        self.uc.mem_write(HANDLE_PA, struct.pack('<I', OUTPUT_PA))
        self.uc.mem_write(OUTPUT_PA, bytes([0xb6])*4096)
        self.uc.mem_write(CTX_PA+0x10c, struct.pack('<I', HANDLE if handle else 0))
        flags = struct.unpack('<I', bytes(self.uc.mem_read(CTX_PA+0x130, 4)))[0] & ~0x20000040
        self.uc.mem_write(CTX_PA+0x130, struct.pack('<I', flags))
        self.context_before = bytes(self.uc.mem_read(CTX_PA, 0x400))

    def code(self, uc, pc, size, user):
        self.pcs.append(pc)
        if pc == STOP:
            return self.stop('returned')
        if pc == IMAGE+0x190894:
            return self.stop('boundary: before_unmatched_outer_epilogue')
        if pc == IMAGE+0x19bdd8:
            return self.stop('boundary: before_unknown_GP_parameter_allocation_state')
        if pc == IMAGE+0x1a0890:
            return self.stop('boundary: before_unknown_GP_timing_allocation_state')
        if pc == IMAGE+0xae50:
            return self.stop('boundary: before_unexecuted_original_assertion')
        if pc in (IMAGE+0x1a085c, IMAGE+0x19bda4):
            x0, x1 = uc.reg_read(reg.UC_MIPS_REG_A0), uc.reg_read(reg.UC_MIPS_REG_A1)
            entry = {'pc': hex(pc), 'a0': hex(x0), 'a1': hex(x1),
                     'LR': hex(uc.reg_read(reg.UC_MIPS_REG_RA)),
                     'SP': hex(uc.reg_read(reg.UC_MIPS_REG_SP))}
            assert x0 == CTX+0x108
            if pc == IMAGE+0x1a085c:
                assert STACK <= x1 and x1+8 <= STACK+0x10000
                entry['argument_bytes_read_after_stop'] = True
            else:
                assert x1 == CTX+0x18c and entry['LR'] == hex(IMAGE+0x1908c0)
            self.entries.append(entry)
        off = pc-IMAGE
        assert any(lo <= off and off+size <= hi for lo, hi in (
            (0x18fdb4, 0x190050), (0x18faa0, 0x18fb34),
            (0x19bda4, 0x19bf68), (0x1a085c, 0x1a09f4),
            (0x190888, 0x190894), (0x1908b8, 0x1908f0)))
        # Executable mapping is RX throughout execution and whole-image bytes
        # are checked after each stop; keep observer reads out of CPU callbacks.
        raw = self.blob[off:off+size]
        ins = next(self.md.disasm(raw, pc), None)
        assert ins is not None and ins.mnemonic not in {
            'syscall', 'break', 'cache', 'sync', 'mfc0', 'mtc0', 'eret',
            'wait', 'tlbwi', 'tlbwr', 'tlbr', 'tlbp'}

    def load(self, uc, access, at, size, value, user):
        assert any(lo <= at and at+size <= hi for lo, hi in (
            (0, len(self.blob)), (INPUT_PA, INPUT_PA+64), (CTX_PA, CTX_PA+0x400),
            (HANDLE_PA, HANDLE_PA+4), (OUTPUT_PA, OUTPUT_PA+4096),
            (STACK_PA, STACK_PA+0x10000)))
        self.reads.append({'pc': hex(uc.reg_read(reg.UC_MIPS_REG_PC)),
                           'physical_address': hex(at), 'bytes': size})

    def store(self, uc, access, at, size, value, user):
        if not any(lo <= at and at+size <= hi for lo, hi in (
            (CTX_PA+1, CTX_PA+2), (CTX_PA+0x198, CTX_PA+0x19c),
            (CTX_PA+0x280, CTX_PA+0x284), (CTX_PA+0x130, CTX_PA+0x134),
            (OUTPUT_PA+0x1c, OUTPUT_PA+0x140), (OUTPUT_PA+0x7d0, OUTPUT_PA+0x7d8),
            (STACK_PA, STACK_PA+0x10000))):
            raise AssertionError((hex(at), size))
        self.stores.append({'pc': hex(uc.reg_read(reg.UC_MIPS_REG_PC)),
                            'physical_address': hex(at), 'bytes': size,
                            'value_low_bits': hex(value & ((1 << (8*size))-1))})

    def phase(self, label, entry):
        self.reason = None
        self.pcs, self.reads, self.stores, self.entries = [], [], [], []
        start_sp = self.uc.reg_read(reg.UC_MIPS_REG_SP)
        self.uc.emu_start(IMAGE+entry, 0, count=20000, timeout=1000000)
        assert self.reason is not None
        for item in self.entries:
            if item['pc'] == hex(IMAGE+0x1a085c):
                at = int(item['a1'],16)-IMAGE
                item['native_argument8_hex'] = bytes(self.uc.mem_read(at,8)).hex()
                assert item['native_argument8_hex'] == '80a90300481f0000'
        assert bytes(self.uc.mem_read(0, len(self.blob))) == self.blob
        assert bytes(self.uc.mem_read(INPUT_PA, 64)) == self.prefix
        assert bytes(self.uc.mem_read(HANDLE_PA, 4)) == struct.pack('<I', OUTPUT_PA)
        return {'label': label, 'entry': hex(IMAGE+entry), 'reason': self.reason,
                'pc': hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'SP_before': hex(start_sp), 'SP_after': hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
                'pcs': [hex(x) for x in self.pcs], 'reads': self.reads,
                'stores': self.stores, 'native_entries': self.entries,
                'original_image_input_and_declared_handle_unchanged': True,
                'native_output_PC_or_service_return_adapter': False}


def one_case(blob, prefix, seed, label, handle, source_index, mutated=False):
    m = Guest(blob, prefix, seed, handle)
    global CURRENT_GUEST
    CURRENT_GUEST = m
    first = m.phase('complete original QoS dispatch '+label, 0x18fdb4)
    mask = struct.unpack_from('<I', prefix)[0]
    expected = bytearray(m.context_before)
    output = bytearray([0xb6])*4096
    if mask == 0x80:
        assert first['reason'] == 'returned'
        expected[1] = 1
        expected[0x198:0x19c] = prefix[0x18:0x1c]
        struct.pack_into('<I', expected, 0x280, struct.unpack_from('<I', expected, 0x280)[0] | 0x20000000)
    elif mask == 0x100:
        assert len(first['native_entries']) == 1
        if handle:
            assert first['reason'] == 'returned'
            assert hex(IMAGE+0x1a09ec) in first['pcs']
            output[0x7d0:0x7d8] = bytes.fromhex('80a90300481f0000')
            struct.pack_into('<I', expected, 0x130, struct.unpack_from('<I', expected, 0x130)[0] | 0x20000000)
        else:
            assert first['reason'] == 'boundary: before_unknown_GP_timing_allocation_state'
    else:
        assert mask == 0 and first['reason'] == 'returned'
    assert bytes(m.uc.mem_read(CTX_PA, 0x400)) == bytes(expected)
    assert bytes(m.uc.mem_read(OUTPUT_PA, 4096)) == bytes(output)
    if first['reason'] == 'returned':
        assert first['SP_after'] == hex(SP)
        assert all(m.uc.reg_read(at) == value for at, value in m.saved.items())
    phases = [first]
    pending_before_upper = expected[1]
    if mask != 0x100:
        # Explicit independent post-dispatch entry. No outer stack frame is
        # invented; stop BEFORE its epilogue. The lower callee really returns
        # to1908c0 in this same phase, with no synthetic success register.
        m.uc.reg_write(reg.UC_MIPS_REG_SP, UPPER_SP)
        m.uc.reg_write(reg.UC_MIPS_REG_RA, STOP)
        m.uc.reg_write(reg.UC_MIPS_REG_S2, CTX)
        m.uc.reg_write(reg.UC_MIPS_REG_S3, CTX+0x108)
        saved_upper = {at: m.uc.reg_read(at) for at in m.saved}
        second = m.phase('independent original upper pending drain '+label, 0x190888)
        phases.append(second)
        if mask == 0x80 and not handle:
            assert second['reason'] == 'boundary: before_unknown_GP_parameter_allocation_state'
            assert len(second['native_entries']) == 1
        else:
            assert second['reason'] == 'boundary: before_unmatched_outer_epilogue'
            assert second['SP_after'] == hex(UPPER_SP)
            assert all(m.uc.reg_read(at) == value for at, value in saved_upper.items())
            if mask == 0x80:
                assert len(second['native_entries']) == 1
                output[0x1c:0x140] = expected[0x18c:0x2b0]
                expected[1] = 0
                struct.pack_into('<I', expected, 0x130, struct.unpack_from('<I', expected, 0x130)[0] | 0x40)
                assert hex(IMAGE+0x1908cc) in second['pcs']
            else:
                assert not second['native_entries']
        assert bytes(m.uc.mem_read(CTX_PA, 0x400)) == bytes(expected)
        assert bytes(m.uc.mem_read(OUTPUT_PA, 4096)) == bytes(output)
    actual = bytes(m.uc.mem_read(CTX_PA, 0x400))
    backend_flags = struct.unpack_from('<I', actual, 0x130)[0]
    return {
        'label': label, 'seed': seed, 'source_case_index': source_index,
        'source_prefix64_hex': prefix.hex(), 'source_mask_only_mutated': mutated,
        'declared_existing_handle': handle, 'phases': phases,
        'context_before_hex': m.context_before.hex(), 'context_after_hex': actual.hex(),
        'output4096_hex': bytes(output).hex(),
        'pending_before_upper': pending_before_upper, 'pending_after': actual[1],
        'backend_parameter_flag40': bool(backend_flags & 0x40),
        'backend_timing_flag20000000': bool(backend_flags & 0x20000000),
        'encoded_target_decoded': a.decode(struct.unpack_from('<I', actual, 0x198)[0]),
        'whole_context_and_output_match_only_declared_native_effects': True,
        'actual_live_flow_driver_initialization_physical_mapping_hardware_ack_or_recording_proven': False,
    }


def run(out):
    prior = BASE/'stage79-vcd-qos-consumption/final-receipt.json'
    assert im.sha(prior.read_bytes()) == '3e43f278545b3d7e1bba4892a248ae8e2716883acfb741b6fe0bdcfa44aa9157'
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes()) == row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes() == (STAGE/'goal-status-before.json').read_bytes()
    source_path = BASE/'stage78-native-start-flags-and-query-tail/run-20261026/start-flags-results.json'
    source = json.loads(source_path.read_text())
    blob = a.v.VCD_PATH.read_bytes()
    assert im.sha(blob) == im.PINS[str(a.v.VCD_PATH.relative_to(BASE))]
    cases = []
    for x in source['cases']:
        for i in (0, 1, 2):
            prefix = bytes.fromhex(x['cases'][i]['extra_first64_hex'])
            cases.append(one_case(blob, prefix, x['seed'], x['cases'][i]['label'], True, i))
        prefix = bytearray.fromhex(x['cases'][2]['extra_first64_hex'])
        struct.pack_into('<I', prefix, 0, 0)
        cases.append(one_case(blob, bytes(prefix), x['seed'], 'retained20M cleared mask control', True, 2, True))
        prefix = bytes.fromhex(x['cases'][2]['extra_first64_hex'])
        cases.append(one_case(blob, prefix, x['seed'], '20M without backend handle', False, 2))
        prefix = bytes.fromhex(x['cases'][3]['extra_first64_hex'])
        cases.append(one_case(blob, prefix, x['seed'], 'native query tail with existing handle', True, 3))
        cases.append(one_case(blob, prefix, x['seed'], 'native query tail without handle', False, 3))
    result = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'PASS_NATIVE_PENDING_CLEAR_BACKEND_FLAGS_RETAINED_AND_TIMING_COPY',
        'cases': cases, 'bounded_phases': sum(len(x['phases']) for x in cases),
        'whole_QoS_dispatch_returns': sum(x['phases'][0]['reason']=='returned' for x in cases),
        'source_receipt': {'script_sha256': im.sha(Path(__file__).read_bytes()),
                           'prior_runner_sha256': im.sha((a.STAGE/'vcd_qos.py').read_bytes()),
                           'stage78_result_sha256': im.sha(source_path.read_bytes()), 'VCD_sha256': im.sha(blob)},
        'timing_original_words': [
            {'offset': hex(at), 'bytes': blob[at:at+4].hex(),
             'asm': next((i.mnemonic+' '+i.op_str for i in cs.Cs(
                 cs.CS_ARCH_MIPS, cs.CS_MODE_MIPS32 | cs.CS_MODE_LITTLE_ENDIAN).disasm(
                     blob[at:at+4], IMAGE+at)), None)}
            for at in range(0x1a085c, 0x1a09f4, 4)],
        'original_upper_fragment': a.v.mips_dump(blob, 0x190888, 0x1908f0),
        'scope': [
            'Original QoS target preparation is followed by an independent upper pending-drain fragment; original19bda4 genuinely returns to1908c0, then1908cc clears only the outer pending byte.',
            'Pending0 coexists with backend flag40 and retained292-byte output. This is parameter transfer, not hardware completion or safe release.',
            'Original1a085c with declared existing handle copies native240000/8008 bytes to output7d0 and sets backend bit29. Outer pending remains0; distinct flags are not interchangeable.',
            'Missing-handle cases stop before GP loads in target/timing allocation paths. No fabricated task, allocation, opaque opcode, MMIO or callback return.',
            'Component/handle/physical buffer are declared fixtures. No full128-byte transport, valid complete hardware packet, actual initialization/shared sync/Start/recording or recovery proof.'],
        'Windows_UU_camera_operations': False, 'goal_complete': False, 'persistent_write_release': False,
    }
    im.write_json(out/'pending-timing-results.json', result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status': result['status'], 'cases': len(cases), 'bounded_phases': result['bounded_phases'],
                      'hardware_completion_or_recording_proven': False}))


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
                                                    'SP': hex(m.uc.reg_read(reg.UC_MIPS_REG_SP)),
                                                    'RA': hex(m.uc.reg_read(reg.UC_MIPS_REG_RA)),
                                                    'reason': m.reason, 'last_pcs': [hex(x) for x in m.pcs[-24:]],
                                                    'all_pcs': [hex(x) for x in m.pcs],
                                                    'last_stack_stores': [x for x in m.stores if STACK_PA <= int(x['physical_address'],16) < STACK_PA+0x10000][-48:],
                                                    'stack_SP_minus_0x100_hex': bytes(m.uc.mem_read(SP-IMAGE-0x100,0x100)).hex(),
                                                    'native_entries': m.entries})
        raise


if __name__ == '__main__':
    main()
