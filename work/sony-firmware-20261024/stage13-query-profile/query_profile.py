#!/usr/bin/env python3
"""Device-free query/profile consistency experiment; never exports firmware.

Runs pinned original AArch64 query/search functions with synthetic inputs and a
guest-only candidate branch. No USB, filesystem-in-guest, syscall or MMIO bridge.
Unlike the earlier query harness, both mode predicates and hash lookup execute
their original instructions. A synthetic hash container holds only the original
literal key/value pairs; it is not a captured camera/container or its constructor.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import plistlib
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
STAGE = Path(__file__).resolve().parent
BASE = ROOT / 'work/sony-firmware-20261024'
P12 = BASE / 'stage12-prototype/profile'
V4 = BASE / 'stage4-windows-collab/mac-verification'
sys.path[:0] = [str(P12), str(V4)]
import profile_prototype as pp
from offline_verify import APP, MPR, SCRATCH, STACK, STOP, LITERAL_PAIRS, read32
import unicorn.arm64_const as reg

QUERY_ENTRY = 0x2e68048
QUERY_SITE = 0x2e68094
QUERY_END = 0x2e69ef0
EPILOGUE = 0x2e69ebc
SQ_PREDICATE = 0x2a4e798
MOVIE_PREDICATE = 0x2a4e6b0
LOOKUP = 0x2e68010
BEFORE_NODE = 0x2e56d80
MAP_GLOBAL = 0x968b890
ASSERT = 0x2f6fe3c
CODE = pp.CODE + 0x600
BUCKETS, SENTINELS, NODES = SCRATCH + 0x4000, SCRATCH + 0x5000, SCRATCH + 0x6000
BUCKET_COUNT = 31
EXPECTED_VOLUME = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verify_volume():
    x = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert x['VolumeUUID'] == EXPECTED_VOLUME and x['MountPoint'] == '/Volumes/KAFU2T'


def new_patch():
    """Intercept only the new ordinary-movie HS30 selector, after real prologue."""
    a = pp.Asm(CODE)
    a.cmp(1, 6)
    a.branch('stock', cond=1)
    a.cmp(22, 2)
    a.branch('stock', cond=1)
    a.cmp(0, 16)
    a.branch('stock', cond=8)  # unsigned HI: preserve the original invalid-mode path
    a.emit(0xa9bf2be9)        # stp x9,x10,[sp,#-16]!
    a.emit(0x2a0003e9)        # mov w9,w0 (original mode)
    a.branch(MOVIE_PREDICATE, link=True)
    a.cmp(0, 0)
    a.branch('stock_saved', cond=0)
    a.emit(0xa8c12be9)        # ldp x9,x10,[sp],#16
    a.mov(0, 6)
    a.str(0, 19, 0)          # VideoParamComb
    a.str(0, 20, 0)          # VQuality
    a.mov(0, 3)
    a.str(0, 21, 0)          # FrameRate, like the original final scalar write
    a.branch(EPILOGUE)
    a.label('stock_saved')
    a.emit(0x2a0903e0)        # mov w0,w9
    a.emit(0xa8c12be9)
    a.label('stock')
    a.branch(SQ_PREDICATE, link=True)
    a.branch(QUERY_SITE + 4)
    raw = a.finish()
    original = pp.Asm(QUERY_SITE)
    original.branch(SQ_PREDICATE, link=True)
    assert APP.read(QUERY_SITE, 4) == original.finish()
    decoded = list(APP.md.disasm(raw, CODE))
    assert len(decoded) == len(raw) // 4
    assert decoded[6].mnemonic == 'stp' and decoded[6].op_str == 'x9, x10, [sp, #-0x10]!'
    assert decoded[11].mnemonic == 'ldp' and decoded[11].op_str == 'x9, x10, [sp], #0x10'
    return (QUERY_SITE, CODE, raw), [
        {'pc': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
        for i in decoded
    ]


def prepare_map(uc):
    """Synthetic before-node buckets, faithful to the two original read routines."""
    groups = {}
    for index, (key, value) in enumerate(LITERAL_PAIRS):
        groups.setdefault(key % BUCKET_COUNT, []).append((index, key, value))
    uc.mem_write(MAP_GLOBAL, struct.pack('<QQ', BUCKETS, BUCKET_COUNT))
    for bucket, values in groups.items():
        sentinel = SENTINELS + bucket * 16
        uc.mem_write(BUCKETS + bucket * 8, struct.pack('<Q', sentinel))
        uc.mem_write(sentinel, struct.pack('<Q', NODES + values[0][0] * 32))
        for n, (index, key, value) in enumerate(values):
            following = NODES + values[n + 1][0] * 32 if n + 1 < len(values) else 0
            uc.mem_write(NODES + index * 32, struct.pack('<QII', following, key, value))


RANGES = [
    (QUERY_ENTRY, QUERY_END), (LOOKUP, QUERY_ENTRY), (BEFORE_NODE, 0x2e56dd4),
    (MOVIE_PREDICATE, 0x2a4e6e4), (0x2a4e794, 0x2a4e798),
    (SQ_PREDICATE, 0x2a4e7cc), (0x2a4e87c, 0x2a4e880),
]


class QueryMicro(pp.StrictMicro):
    def code(self, u, address, size, user):
        if address == ASSERT:
            self.pcs.append(hex(address))
            self.steps += 1
            self.calls.append({'denied_assertion_entry': hex(address)})
            self.abort('firmware assertion entry reached; logger not executed')
            return
        super().code(u, address, size, user)


def lookup_case(key):
    m = QueryMicro(APP, [(LOOKUP, QUERY_ENTRY), (BEFORE_NODE, 0x2e56dd4)])
    prepare_map(m.uc)
    m.uc.mem_write(SCRATCH + 0x3f00, pp.p32(key))
    result = m.run(LOOKUP, [MAP_GLOBAL, SCRATCH + 0x3f00])
    pointer = m.uc.reg_read(reg.UC_ARM64_REG_X0)
    pair = [read32(m.uc, pointer + 8), read32(m.uc, pointer + 12)] if pointer else None
    expected = dict(LITERAL_PAIRS).get(key)
    assert result['reason'] == 'returned'
    assert pair == ([key, expected] if expected is not None else None)
    assert not any(SCRATCH + 0x4000 <= int(w['address'], 16) < SCRATCH + 0x7000 for w in result['stores'])
    return {'key': key, 'pair': pair, 'steps': result['steps'], 'reason': result['reason']}


def query(patch, *, frame, mode=5, fmt=6, q60=12, q24=17, q120=9, other_frames=(0, 0)):
    m = QueryMicro(APP, list(RANGES), patches=[patch] if patch else [])
    prepare_map(m.uc)
    for offset, value in [(0x18, q60), (0x20, q24), (0x28, q120)]:
        m.uc.mem_write(STACK + offset, struct.pack('<Q', value))
    for offset, pointer in [(0x210, SCRATCH), (0x218, SCRATCH + 4), (0x220, SCRATCH + 8)]:
        m.uc.mem_write(STACK + offset, struct.pack('<Q', pointer))
    m.uc.mem_write(SCRATCH, struct.pack('<4I', 0xa5a5a5a5, 0xb6b6b6b6, 0xc7c7c7c7, 0xdeadbeef))
    saved = {}
    for i in range(19, 30):
        saved[i] = 0xd100000000000000 + i
        m.uc.reg_write(getattr(reg, f'UC_ARM64_REG_X{i}'), saved[i])
    m.uc.reg_write(reg.UC_ARM64_REG_X9, 0x1122334455667788)
    m.uc.reg_write(reg.UC_ARM64_REG_X10, 0x8877665544332211)
    result = m.run(QUERY_ENTRY, [mode, fmt, 0, frame, *other_frames, 0, 0])
    vpc, frame_out, quality = struct.unpack('<3I', bytes(m.uc.mem_read(SCRATCH, 12)))
    assert read32(m.uc, SCRATCH + 12) == 0xdeadbeef
    if result['reason'] == 'returned':
        assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK
        assert all(m.uc.reg_read(getattr(reg, f'UC_ARM64_REG_X{i}')) == value for i, value in saved.items())
    result.update(
        input={'mode': mode, 'format': fmt, 'typed_HS_frame': frame, 'quality60': q60,
               'quality24': q24, 'quality120': q120, 'other_frame_args': list(other_frames)},
        candidate_enabled=bool(patch),
        output_vpc_quality_frame=[vpc, quality, frame_out],
        map_lookup_calls=result['pcs'].count(hex(LOOKUP)),
        output_writes=[w for w in result['stores'] if int(w['address'], 16) in (SCRATCH, SCRATCH + 4, SCRATCH + 8)],
        sp_restored=m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK,
        x9_x10=[hex(m.uc.reg_read(getattr(reg, f'UC_ARM64_REG_X{i}'))) for i in (9, 10)],
    )
    return result


def equivalent(left, right):
    return all(left[k] == right[k] for k in ('reason', 'stop_pc', 'output_vpc_quality_frame', 'return_u32', 'x9_x10'))


def write_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New, nonexistent directory under this stage')
    args = parser.parse_args()
    verify_volume()
    output = Path(args.output).resolve()
    assert output != STAGE and STAGE in output.parents and not output.exists()
    output.mkdir()
    originals = {str(n.path.relative_to(ROOT)): sha(n.path) for n in (APP, MPR)}
    dependencies = [P12 / 'profile_prototype.py', P12 / 'profile-results.json',
                    V4 / 'offline_verify.py', BASE / 'stage11-model/builder/audit_typed_builder.py']
    before = {str(p.relative_to(ROOT)): sha(p) for p in dependencies}
    patch, instructions = new_patch()
    lookup_tests = [lookup_case(k) for k, _ in LITERAL_PAIRS] + [lookup_case(k) for k in (0, 17, 43, 1000)]
    prior = json.loads((P12 / 'profile-results.json').read_text())
    stocks = []
    for old in prior['legitimate_HS_cases']:
        case = old['case']
        left, right = query(None, **case), query(patch, **case)
        expected = old['stock_setter']['output_vpc_quality_frame']
        assert left['reason'] == 'returned' and right['reason'] == 'returned'
        assert left['output_vpc_quality_frame'] == expected == right['output_vpc_quality_frame']
        assert equivalent(left, right)
        stocks.append({'case': case, 'expected_from_stage12_actual_setter': expected,
                       'stock_query': left, 'candidate_query': right, 'unchanged': True})
    targets = []
    for q in range(32):
        row = query(patch, frame=2, q60=q)
        assert row['reason'] == 'returned' and row['output_vpc_quality_frame'] == [6, 6, 3]
        assert row['map_lookup_calls'] == 0
        targets.append(row)
    for mode in (6, 7, 8, 9, 15):
        row = query(patch, frame=2, mode=mode, q60=29, q24=2, q120=2)
        assert row['reason'] == 'returned' and row['output_vpc_quality_frame'] == [6, 6, 3]
        targets.append(row)
    controls = []
    for case in [
        {'frame': 3}, {'frame': 7}, {'frame': 2, 'mode': 0}, {'frame': 2, 'mode': 4},
        {'frame': 2, 'mode': 10}, {'frame': 2, 'mode': 16}, {'frame': 2, 'mode': 17},
        {'frame': 2, 'fmt': 7}, {'frame': 2, 'fmt': 8},
    ]:
        left, right = query(None, **case), query(patch, **case)
        assert equivalent(left, right)
        controls.append({'case': case, 'stock': left, 'candidate': right, 'same_observed_outcome': True})
    stock_target = query(None, frame=2)
    assert stock_target['reason'].startswith('firmware assertion entry reached')
    im = pp.Image()
    patches = pp.trampolines(im)
    builder = pp.builder(im, patches, 2, poison=True)
    setter = pp.setter(im, patches, builder['builder_tuple'])
    query_tuple = targets[0]['output_vpc_quality_frame']
    assert builder['builder_tuple'] == [15, 6, 2, 0]
    assert setter['output_vpc_quality_frame'] == query_tuple == [6, 6, 3]
    downstream = pp.downstream(query_tuple, logging_adapter=True)
    assert all(downstream[k]['reason'] == 'returned' for k in
               ('validator', 'main_codec', 'bitrate', 'rational', 'open_parameter_preparation'))
    fields = downstream['open_parameter_preparation']['fields']
    assert fields['codec'] == 15
    assert fields['width'] == 1920 and fields['height'] == 1080
    assert fields['chroma'] == 0 and fields['bitdepth'] == 1
    assert downstream['bitrate']['return_u32'] == 16000
    assert [downstream['rational'][k] for k in ('numerator', 'denominator')] == [30000, 1001]
    after = {str(n.path.relative_to(ROOT)): sha(n.path) for n in (APP, MPR)}
    assert originals == after
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in dependencies}
    results = {
        'status': 'PASS_CPU_ONLY_QUERY_PROFILE_COMPONENT',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Modified guest query helper, synthetic model/container/arguments; not full caller, remaining-time calculation, menu, save, encoder or camera',
        'input_hashes_before': originals, 'input_hashes_after': after,
        'dependencies_unchanged': before,
        'guest_patch': {'site': hex(QUERY_SITE), 'original': APP.read(QUERY_SITE, 4).hex(),
                        'scratch_address_not_device_cave': hex(CODE), 'instructions': instructions,
                        'guard': 'format6 + typed HS frame2 + original ordinary-movie predicate'},
        'synthetic_map': {'global': hex(MAP_GLOBAL), 'bucket_count': BUCKET_COUNT,
                          'literal_table': '0x39898b0', 'pairs': LITERAL_PAIRS,
                          'constructor_or_live_state_reconstructed': False,
                          'actual_lookup_instructions_executed': True, 'lookup_adapter': False},
        'lookup_tests': lookup_tests, 'stock_regressions': stocks,
        'target_cases': targets, 'controls': controls, 'original_target_assertion': stock_target,
        'builder_target': builder, 'setter_target': setter, 'query_target_to_MPR': downstream,
        'query_stubs': [],
        'mpr_logging_adapter': 'Reuse stage12 single-address PC<-LR logging adapter; no outputs/register return values written',
        'source_unchanged': True, 'hardware_or_camera_actions': False,
        'firmware_payload_or_patchfile_exported': False, 'goal_complete': False,
    }
    write_json(output / 'query-results.json', results)
    summary = {'status': results['status'], 'lookup_tests': len(lookup_tests),
               'stock_HS_regressions': len(stocks), 'target_queries': len(targets),
               'control_pairs': len(controls), 'query_tuple_equals_setter_tuple': query_tuple,
               'full_remaining_time_or_callers_executed': False,
               'source_unchanged': True, 'goal_complete': False}
    write_json(output / 'summary.json', summary)
    write_json(output / 'source-receipt.json', {
        'script': str(Path(__file__).relative_to(ROOT)), 'script_sha256': sha(__file__),
        'results_sha256': sha(output / 'query-results.json'), 'summary_sha256': sha(output / 'summary.json'),
        'originals': originals, 'dependencies': before, 'volume_uuid': EXPECTED_VOLUME,
        'guest_function_emulation': True, 'camera_native_execution': False,
    })
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
