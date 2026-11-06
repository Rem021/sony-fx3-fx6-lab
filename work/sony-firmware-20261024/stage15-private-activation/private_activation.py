#!/usr/bin/env python3
"""Guest-only private activation experiment, not a camera loader or firmware.

The private flag and code pages are synthetic mappings, not installation
addresses. All model values remain factory-legal. Consistent flag snapshots
are tested separately from mixed-snapshot counterexamples; no concurrency,
real mode transition, persistence, WBI, encoder or recovery is implemented.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE / 'stage13-query-profile'), str(BASE / 'stage12-prototype/profile'),
               str(BASE / 'stage4-windows-collab/mac-verification')]
import query_profile as qp
import profile_prototype as pp
from offline_verify import APP, MPR, SCRATCH, STACK, STACK_BASE, read32
import unicorn.arm64_const as reg

FLAG = SCRATCH + 0xf000
TARGET = [15, 6, 2, 0]
ENCODING = [6, 6, 3]
MOVIE_MODES = [5, 6, 7, 8, 9, 15]
SAVE = (0xa9bd07e0, 0xa9010fe2, 0xa9027be4)
RESTORE = (0xa9427be4, 0xa9410fe2, 0xa8c307e0)


def load_flag(a):
    # movz x0,#0xf000; movk x0,#0x1100,lsl#16; ldr w0,[x0]
    assert FLAG == 0x1100f000
    a.emit(0xd2800000 | 0xf000 << 5)
    a.emit(0xf2a00000 | 0x1100 << 5)
    a.ldr(0, 0, 0)


def patches(im):
    assert im.read(pp.BUILDER_SITE, 4).hex() == '61160051'
    assert im.read(pp.SETTER_SITE, 4).hex() == 'a0008052'
    a = pp.Asm(pp.CODE)
    for word in SAVE: a.emit(word)
    a.cmp(19, 6); a.branch('stock', cond=1)
    load_flag(a); a.cmp(0, 1); a.branch('stock', cond=1)
    a.branch(0x2bd0fe0, link=True); a.ldr(0, 0, 0)
    a.cmp(0, 16); a.branch('stock', cond=8)
    a.branch(qp.MOVIE_PREDICATE, link=True)
    a.cmp(0, 0); a.branch('stock', cond=0)
    for value, offset in zip(TARGET, (0x40, 0x44, 0x48, 0x4c)):
        a.mov(0, value); a.str(0, 24, offset)
    for word in RESTORE: a.emit(word)
    a.mov(0, 2)  # As in prior prototype; full caller scalar-return use unverified.
    a.branch(0x2bec2f0)
    a.label('stock')
    for word in RESTORE: a.emit(word)
    a.emit(struct.unpack('<I', im.read(pp.BUILDER_SITE, 4))[0])
    a.branch(pp.BUILDER_SITE + 4)

    b = pp.Asm(pp.CODE + 0x200)
    load_flag(b); b.cmp(0, 1); b.branch('stock', cond=1)
    for offset, value in zip((0x10, 0x14, 0x18, 0x1c), TARGET):
        b.ldr(0, 24, offset); b.cmp(0, value); b.branch('stock', cond=1)
    b.mov(0, 6); b.branch(pp.SETTER_SITE + 4)
    b.label('stock'); b.emit(struct.unpack('<I', im.read(pp.SETTER_SITE, 4))[0])
    b.branch(pp.SETTER_SITE + 4)

    c = pp.Asm(qp.CODE)
    c.cmp(1, 6); c.branch('stock', cond=1)
    c.cmp(0, 16); c.branch('stock', cond=8)
    c.emit(0xa9bf2be9); c.emit(0x2a0003e9)  # save x9/x10 and original mode
    load_flag(c); c.cmp(0, 1); c.branch('stock_saved', cond=1)
    c.emit(0x2a0903e0)
    c.branch(qp.MOVIE_PREDICATE, link=True)
    c.cmp(0, 0); c.branch('stock_saved', cond=0)
    c.emit(0xa8c12be9)
    c.mov(0, 6); c.str(0, 19, 0); c.str(0, 20, 0)
    c.mov(0, 3); c.str(0, 21, 0); c.branch(qp.EPILOGUE)
    c.label('stock_saved'); c.emit(0x2a0903e0); c.emit(0xa8c12be9)
    c.label('stock'); c.branch(qp.SQ_PREDICATE, link=True); c.branch(qp.QUERY_SITE + 4)
    original = pp.Asm(qp.QUERY_SITE); original.branch(qp.SQ_PREDICATE, link=True)
    assert APP.read(qp.QUERY_SITE, 4) == original.finish()
    result = [(pp.BUILDER_SITE, pp.CODE, a.finish()),
              (pp.SETTER_SITE, pp.CODE + 0x200, b.finish()),
              (qp.QUERY_SITE, qp.CODE, c.finish())]
    assert all(address + len(raw) <= next_address for (_, address, raw), next_address in
               zip(result, (pp.CODE + 0x200, qp.CODE, pp.CODE + 4096)))
    checks = [
        'stp x0, x1, [sp, #-0x30]!', 'stp x2, x3, [sp, #0x10]',
        'stp x4, x30, [sp, #0x20]', 'ldp x4, x30, [sp, #0x20]',
        'ldp x2, x3, [sp, #0x10]', 'ldp x0, x1, [sp], #0x30']
    for word, expected in zip(SAVE + RESTORE, checks):
        ins = next(APP.md.disasm(pp.p32(word), 0))
        assert ins.mnemonic + ' ' + ins.op_str == expected
    return result


class FlagMixin:
    def __init__(self, *args, profile_flag=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_flag = profile_flag
        self.uc.mem_write(FLAG, pp.p32(profile_flag))

    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        assert read32(self.uc, FLAG) == self.profile_flag
        assert not any(int(w['address'], 16) < FLAG + 4 and
                       FLAG < int(w['address'], 16) + w['size'] for w in result['stores'])
        result['synthetic_private_flag'] = self.profile_flag
        result['private_flag_written_by_guest'] = False
        return result


class FlagApp(FlagMixin, pp.StrictMicro): pass
class FlagQuery(FlagMixin, qp.QueryMicro): pass


def builder(im, patchset, *, frame, q60=12, q24=17, q120=9, fmt=6,
            exposure=5, flag=0, poison=False):
    leaves = json.loads((pp.B11 / 'model-leaf-accessors.json').read_text())['accessors']
    addresses = {int(x['accessor'], 16) for x in leaves} | {0x2934c9c, 0x29353a4, 0x293d90c}
    ranges = [(pp.BUILDER_ENTRY, 0x2beea04), (0x2bd0fb0, 0x2bd0ff8),
              (0x2a4e5e0, 0x2a4e600), (0x2a4e6b0, 0x2a4e6e4),
              (0x2a4e794, 0x2a4e7cc), (0x2a4e87c, 0x2a4e880)] + [(a, a + 20) for a in addresses]
    m = FlagApp(APP, ranges, patches=patchset[:1], profile_flag=flag)
    values = {0x2934c9c: fmt, 0x293d90c: exposure, pp.FRAMEGET: frame,
              pp.Q60: q60, pp.Q24: q24, pp.Q120: q120}
    seeded = {im.leaf(a): values.get(a, 0) for a in addresses}
    for a, value in seeded.items(): m.uc.mem_write(a, pp.p32(value))
    defaults = [0xfefefefe] * 4 if poison else [15, 6, 24, 0]
    m.uc.mem_write(SCRATCH + 0x40, struct.pack('<4I', *defaults))
    result = m.run(pp.BUILDER_ENTRY, [SCRATCH, 0])
    assert all(read32(m.uc, a) == value for a, value in seeded.items())
    blob = bytes(m.uc.mem_read(SCRATCH, 0x1000))
    result.update(builder_tuple=list(struct.unpack('<4I', blob[0x40:0x50])),
                  full_builder_sha256=hashlib.sha256(blob).hexdigest(),
                  original_model_cells_unchanged=True,
                  sp_restored=m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK)
    if result['reason'] == 'returned': assert result['sp_restored']
    return result


def setter(im, patchset, values, *, flag=0):
    m = FlagApp(APP, [(pp.SETTER_ENTRY, pp.SETTER_END), (0x2e6f45c, 0x2e6f494)],
                end=pp.SETTER_END, patches=patchset[1:2], profile_flag=flag)
    base = STACK_BASE + 0x10000
    m.uc.mem_write(SCRATCH + 0x10, struct.pack('<4I', *values))
    for r, value in [(reg.UC_ARM64_REG_X24, SCRATCH), (reg.UC_ARM64_REG_X29, base),
                     (reg.UC_ARM64_REG_X19, base + 0x310)]: m.uc.reg_write(r, value)
    result = m.run(pp.SETTER_ENTRY)
    result.update(input_builder_tuple=values,
                  output_vpc_quality_frame=list(struct.unpack('<3I', bytes(m.uc.mem_read(base + 0x480, 12)))))
    return result


def query(patchset, *, frame, mode=5, fmt=6, q60=12, q24=17, q120=9, flag=0):
    m = FlagQuery(APP, list(qp.RANGES), patches=patchset[2:], profile_flag=flag)
    qp.prepare_map(m.uc)
    for offset, value in [(0x18, q60), (0x20, q24), (0x28, q120)]:
        m.uc.mem_write(STACK + offset, struct.pack('<Q', value))
    for offset, pointer in [(0x210, SCRATCH), (0x218, SCRATCH + 4), (0x220, SCRATCH + 8)]:
        m.uc.mem_write(STACK + offset, struct.pack('<Q', pointer))
    m.uc.mem_write(SCRATCH, struct.pack('<4I', 0xa5a5a5a5, 0xb6b6b6b6, 0xc7c7c7c7, 0xdeadbeef))
    saved = {i: 0xd100000000000000 + i for i in range(19, 30)}
    for i, value in saved.items(): m.uc.reg_write(getattr(reg, f'UC_ARM64_REG_X{i}'), value)
    m.uc.reg_write(reg.UC_ARM64_REG_X9, 0x1122334455667788)
    m.uc.reg_write(reg.UC_ARM64_REG_X10, 0x8877665544332211)
    result = m.run(qp.QUERY_ENTRY, [mode, fmt, 0, frame, 0, 0, 0, 0])
    vpc, frame_out, quality = struct.unpack('<3I', bytes(m.uc.mem_read(SCRATCH, 12)))
    assert read32(m.uc, SCRATCH + 12) == 0xdeadbeef
    if result['reason'] == 'returned':
        assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK
        assert all(m.uc.reg_read(getattr(reg, f'UC_ARM64_REG_X{i}')) == value for i, value in saved.items())
    result.update(output_vpc_quality_frame=[vpc, quality, frame_out],
                  x9_x10=[hex(m.uc.reg_read(getattr(reg, f'UC_ARM64_REG_X{i}'))) for i in (9, 10)])
    return result


def same_builder(left, right):
    return all(left[k] == right[k] for k in ('reason', 'stop_pc', 'full_builder_sha256'))


def same_setter(left, right):
    return all(left[k] == right[k] for k in ('reason', 'stop_pc', 'output_vpc_quality_frame'))


def chain(im, ps, case, flags):
    b = builder(im, ps, **case, flag=flags[0])
    s = setter(im, ps, b['builder_tuple'], flag=flags[1])
    q = query(ps, **case, flag=flags[2])
    return {'flag_snapshots_builder_setter_query': list(flags), 'builder': b, 'setter': s, 'query': q,
            'setter_query_equal': s['output_vpc_quality_frame'] == q['output_vpc_quality_frame']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    qp.verify_volume()
    output = Path(args.output).resolve()
    assert STAGE in output.parents and not output.exists()
    output.mkdir()
    inputs = [APP.path, MPR.path, Path(pp.__file__), Path(qp.__file__), pp.V4 / 'offline_verify.py',
              pp.B11 / 'model-leaf-accessors.json', pp.B11 / 'builder-static.json', pp.B11 / 'selection-tables.json']
    hashes = {str(p.relative_to(ROOT)): qp.sha(p) for p in inputs}
    im = pp.Image(); ps = patches(im)
    rows = []
    for case in pp.allowed_cases(im)['cases']:
        stock_b = pp.builder(im, [], **case)
        stock_s = pp.setter(im, [], stock_b['builder_tuple'])
        stock_q = qp.query(None, **case)
        inactive = chain(im, ps, case, (0, 0, 0))
        active = chain(im, ps, case, (1, 1, 1))
        assert same_builder(stock_b, inactive['builder'])
        assert same_setter(stock_s, inactive['setter']) and qp.equivalent(stock_q, inactive['query'])
        assert active['builder']['reason'] == active['query']['reason'] == 'returned'
        assert active['setter']['reason'] == 'conversion block complete'
        assert active['builder']['builder_tuple'] == TARGET
        assert active['setter']['output_vpc_quality_frame'] == active['query']['output_vpc_quality_frame'] == ENCODING
        rows.append({'factory_legal_case': case, 'stock_builder': stock_b, 'stock_setter': stock_s,
                     'stock_query': stock_q, 'inactive': inactive, 'active': active})
    modes = []
    for mode in range(17):
        b0 = builder(im, ps, frame=0, exposure=mode)
        b1 = builder(im, ps, frame=0, exposure=mode, flag=1)
        q0 = query(ps, frame=0, mode=mode)
        q1 = query(ps, frame=0, mode=mode, flag=1)
        if mode in MOVIE_MODES:
            assert b1['builder_tuple'] == TARGET and q1['output_vpc_quality_frame'] == ENCODING
            category = 'target_in_ordinary_movie_fixture'
        else:
            assert same_builder(b0, b1) and qp.equivalent(q0, q1)
            category = ('valid_factory_result_preserved' if mode < 5 else
                        'same_observed_outcome_but_SQ_fixture_incomplete')
        if mode < 5: assert b0['reason'] == q0['reason'] == 'returned'
        modes.append({'mode_value': mode, 'category': category,
                      'inactive_builder': b0, 'active_builder': b1, 'inactive_query': q0, 'active_query': q1})
    controls = []
    for case in ({'frame': 0, 'fmt': 7}, {'frame': 0, 'fmt': 8}, {'frame': 0, 'mode': 17}):
        q0, q1 = query(ps, **case), query(ps, **case, flag=1)
        assert qp.equivalent(q0, q1)
        bc = {('exposure' if k == 'mode' else k): v for k, v in case.items()}
        b0, b1 = builder(im, ps, **bc), builder(im, ps, **bc, flag=1)
        assert same_builder(b0, b1)
        controls.append({'case': case, 'inactive_builder': b0, 'active_builder': b1,
                         'inactive_query': q0, 'active_query': q1})
    invalid = []
    for flag in (2, 0xffffffff):
        result = chain(im, ps, {'frame': 0}, (flag, flag, flag))
        baseline = rows[0]['inactive']
        # rows[0] has a different q60; compare an independent matching stock fixture.
        baseline = chain(im, ps, {'frame': 0}, (0, 0, 0))
        assert same_builder(result['builder'], baseline['builder'])
        assert same_setter(result['setter'], baseline['setter']) and qp.equivalent(result['query'], baseline['query'])
        invalid.append(result)
    setter_controls = []
    for values in ([15, 8, 2, 0], [15, 7, 13, 0], [15, 6, 2, 1], [20, 6, 13, 0],
                   [15, 6, 13, 0], [18, 6, 2, 0], [15, 13, 2, 0], [15, 6, 2, 2]):
        left, right = setter(im, ps, values), setter(im, ps, values, flag=1)
        assert same_setter(left, right)
        setter_controls.append({'input': values, 'inactive': left, 'active': right})
    transitions = [chain(im, ps, {'frame': 0}, flags) for flags in
                   ((0, 0, 0), (1, 1, 1), (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 1))]
    assert all(x['setter_query_equal'] for x in transitions[:3])
    assert all(not x['setter_query_equal'] for x in transitions[3:])
    poison = builder(im, ps, frame=0, flag=1, poison=True)
    assert poison['builder_tuple'] == TARGET
    for offset in (0x40, 0x44, 0x48, 0x4c):
        assert any(int(w['address'], 16) == SCRATCH + offset for w in poison['stores'])
    downstream = pp.downstream(rows[0]['active']['setter']['output_vpc_quality_frame'], logging_adapter=True)
    assert all(downstream[k]['reason'] == 'returned' for k in
               ('validator', 'main_codec', 'bitrate', 'rational', 'open_parameter_preparation'))
    assert downstream['validator']['return_u32'] == 0 and downstream['main_codec']['return_u32'] == 15
    assert downstream['bitrate']['return_u32'] == 16000
    assert [downstream['rational'][k] for k in ('numerator', 'denominator')] == [30000, 1001]
    assert downstream['open_parameter_preparation']['fields'] == {
        'codec': 15, 'width': 1920, 'height': 1080, 'frame_enum': 3, 'ntsc_flag': 1,
        'quality_enum': 22, 'chroma': 0, 'bitdepth': 1}
    assert hashes == {str(p.relative_to(ROOT)): qp.sha(p) for p in inputs}
    proof = {'status': 'PASS_BOUNDED_PRIVATE_FLAG_COMPONENT_WITH_MIXED_SNAPSHOT_COUNTEREXAMPLES',
             'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'scope': 'Pinned original instructions plus own guest-only branches, synthetic inputs and independent flag snapshots',
             'source_hashes_unchanged': hashes,
             'patches_guest_only': [{'site': hex(site), 'synthetic_code_address': hex(address),
                 'instructions': [{'pc': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
                                  for i in APP.md.disasm(raw, address)]} for site, address, raw in ps],
             'private_state': {'synthetic_address_not_camera_cave': hex(FLAG), 'active_value': 1,
                 'values_other_than_one_fall_back': True, 'camera_storage_or_owner_discovered': False},
             'factory_legal_cases': rows, 'mode_fixtures': modes, 'other_context_controls': controls,
             'invalid_flag_cases': invalid, 'setter_controls': setter_controls,
             'independent_snapshot_sequences_not_actual_concurrency': transitions,
             'poisoned_target_buffer': poison, 'actual_guest_setter_output_to_MPR': downstream,
             'synchronization_implemented': False, 'record_idle_gate_implemented': False,
             'full_caller_ABI_menu_or_persistence_verified': False,
             'resetting_emulator_flag_proves_physical_reboot_clears_flag': False,
             'WBI_may_restore_RAM_so_boot_lifetime_requires_separate_evidence': True,
             'camera_USB_native_WBI_or_write_actions': False,
             'firmware_payload_or_patchfile_exported': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'factory_legal_cases_inactive_and_active': len(rows),
               'mode_fixtures': len(modes), 'previous_five_error_contexts_preserved_with_legal_model': list(range(5)),
               'ordinary_movie_mode_fixtures': MOVIE_MODES,
               'SQ_fixture_dependencies_unclosed': [10, 11, 12, 13, 14, 16],
               'other_context_controls': len(controls), 'invalid_flag_controls': len(invalid),
               'setter_controls': len(setter_controls), 'mixed_snapshot_counterexamples': 3,
               'original_model_cells_unchanged_in_all_builder_runs': True,
               'activation_synchronization_or_real_transition_verified': False,
               'hardware_recording_or_recovery_verified': False, 'goal_complete': False}
    qp.write_json(output / 'activation-results.json', proof)
    qp.write_json(output / 'summary.json', summary)
    qp.write_json(output / 'source-receipt.json', {'script': str(Path(__file__).relative_to(ROOT)),
        'script_sha256': qp.sha(Path(__file__)), 'results_sha256': qp.sha(output / 'activation-results.json'),
        'summary_sha256': qp.sha(output / 'summary.json'), 'inputs': hashes,
        'volume_uuid': qp.EXPECTED_VOLUME, 'camera_native_execution': False})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
